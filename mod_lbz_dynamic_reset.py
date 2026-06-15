# -*- coding: utf-8 -*-

import os
import sys
import time
import traceback

MOD_NAME = "LBZ_DYNAMIC_RESET"
MOD_VERSION = "0.1.37"
DEBUG_LOG = False
HOTKEY_COOLDOWN = 0.8
SETTINGS_LINKAGE = "lbz_dynamic_reset"
SETTINGS_TITLE = u"\u0421\u0431\u0440\u043e\u0441 \u041b\u0411\u0417"
MAX_SETTINGS_ROWS = 10

GAME_ROOT = os.getcwd()
CONFIG_DIR = os.path.join(GAME_ROOT, "mods", "configs")
POS_FILE = os.path.join(CONFIG_DIR, "lbz_dynamic_reset_pos_v3.txt")

try:
    import BigWorld
except Exception:
    BigWorld = None

try:
    import Keys
except Exception:
    Keys = None

LAST_KEY_TIME = 0.0
NEXT_INDEX = 0
LAST_POLL_DOWN = False
INPUT_HOOKED = False
RESET_IN_PROGRESS = False
INIT_DONE = False
SETTINGS_REGISTERED = False
SELECTOR_QUESTS = []
SELECTOR_UNTIL = 0.0
SELECTOR_TIMEOUT = 30.0
OVERLAY_COMPONENTS = []
OVERLAY_META = []
OVERLAY_LINES = []
OVERLAY_WANTED = True
OVERLAY_POS = {"x": 0.22, "y": 0.35}
OVERLAY_STEP = 0.060
OVERLAY_MOVE_STEP = 0.04
OVERLAY_POLL_RUNNING = False
OVERLAY_DRAGGING = False
OVERLAY_DRAG_OFFSET = {"x": 0.0, "y": 0.0}
OVERLAY_DRAG_LAST_POS = None
LAST_OVERLAY_MOVE_TIME = 0.0
LAST_OVERLAY_SELECT_TIME = 0.0
LAST_OVERLAY_SAVE_TIME = 0.0
LAST_OVERLAY_REFRESH_TIME = 0.0
LAST_MOUSE_ACTION_TIME = 0.0
MOUSE_POS_ERROR_LOGGED = False
OVERLAY_HOVER_ACTION = None
OVERLAY_HOVER_INDEX = None
OVERLAY_HOVER_START_TIME = 0.0
OVERLAY_HELP_SHOWN = False
OVERLAY_TITLE = u"\u0421\u0431\u0440\u043e\u0441 \u041b\u0411\u0417"
OVERLAY_HELP_TEXT = u"\u041a\u043b\u0438\u043a: \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u043a\u0430\u0440\u0442\u043e\u0447\u043a\u0443. Alt+\u043a\u043b\u0438\u043a: \u0441\u0440\u0430\u0437\u0443 \u0441\u0431\u0440\u043e\u0441. Ctrl+\u041b\u041a\u041c: \u043f\u0435\u0440\u0435\u043c\u0435\u0441\u0442\u0438\u0442\u044c. F9: \u0441\u043a\u0440\u044b\u0442\u044c/\u043f\u043e\u043a\u0430\u0437\u0430\u0442\u044c."
ROMAN_LEVELS = {
    1: u"I",
    2: u"II",
    3: u"III",
    4: u"IV",
    5: u"V",
    6: u"VI",
    7: u"VII",
    8: u"VIII",
    9: u"IX",
    10: u"X",
    11: u"XI"
}


def ensure_config_dir():
    try:
        if not os.path.isdir(CONFIG_DIR):
            os.makedirs(CONFIG_DIR)
    except Exception:
        pass


def safe_repr(value, limit=500):
    try:
        text = repr(value)
    except Exception:
        text = "<repr_error>"
    try:
        if len(text) > limit:
            text = text[:limit] + "...<cut>"
    except Exception:
        pass
    return text


def log(message):
    if not DEBUG_LOG:
        return
    try:
        print("[{} {}] {}".format(MOD_NAME, MOD_VERSION, message))
    except Exception:
        pass


def log_exception(title):
    try:
        print("[{} {} ERROR] {}".format(MOD_NAME, MOD_VERSION, title))
        print(traceback.format_exc())
    except Exception:
        pass


def call(obj, method_name, default=None):
    try:
        if hasattr(obj, method_name):
            return getattr(obj, method_name)()
    except Exception:
        pass
    return default


def call_bool(obj, method_name):
    try:
        return bool(call(obj, method_name, False))
    except Exception:
        return False


def to_unicode_text(value):
    try:
        if value is None:
            return u""
        if isinstance(value, unicode):
            return value
        if isinstance(value, str):
            for encoding in ("utf-8", "cp1251"):
                try:
                    return unicode(value, encoding)
                except Exception:
                    pass
        return unicode(value)
    except Exception:
        try:
            return unicode(safe_repr(value, 200))
        except Exception:
            return u""


def first_text_method(obj, method_names):
    for method_name in method_names:
        value = call(obj, method_name, None)
        value = to_unicode_text(value).strip()
        if value:
            return value
    return u""


def trim_text(value, limit):
    try:
        value = to_unicode_text(value).strip()
        if len(value) <= limit:
            return value
        return value[:limit - 3] + u"..."
    except Exception:
        return value


def roman_level(level):
    try:
        return ROMAN_LEVELS.get(int(level), to_unicode_text(level))
    except Exception:
        return u""


def format_vehicle_levels(min_level, max_level):
    try:
        if min_level is None or max_level is None:
            return u""
        min_text = roman_level(min_level)
        max_text = roman_level(max_level)
        if not min_text or not max_text:
            return u""
        if int(min_level) == int(max_level):
            return min_text
        return u"{}-{}".format(min_text, max_text)
    except Exception:
        log_exception("format_vehicle_levels")
        return u""


def get_quest_vehicle_levels(quest):
    min_level = None
    max_level = None

    for method_name in ["getVehMinLevel", "getVehicleMinLevel", "getMinVehicleLevel"]:
        min_level = call(quest, method_name, None)
        if min_level is not None:
            break

    for method_name in ["getVehMaxLevel", "getVehicleMaxLevel", "getMaxVehicleLevel"]:
        max_level = call(quest, method_name, None)
        if max_level is not None:
            break

    return format_vehicle_levels(min_level, max_level)


def get_controller():
    try:
        from helpers import dependency
        from skeletons.gui.game_control import IPersonalMissionsController
        return dependency.instance(IPersonalMissionsController)
    except Exception:
        log_exception("get_controller")
        return None


def get_current_vehicle():
    try:
        from CurrentVehicle import g_currentVehicle
        return g_currentVehicle
    except Exception:
        log_exception("get_current_vehicle")
        return None


def is_hangar_context():
    try:
        if BigWorld is not None:
            player = BigWorld.player()
            class_name = player.__class__.__name__ if player is not None else ""
            if class_name and "account" not in class_name.lower():
                log("not hangar: player class {}".format(class_name))
                return False
    except Exception:
        pass

    try:
        from helpers import dependency
        from skeletons.gui.app_loader import IAppLoader
        app = dependency.instance(IAppLoader).getApp()
        app_text = safe_repr(app, 200).lower()
        if "battle" in app_text and "lobby" not in app_text:
            log("not hangar: app {}".format(safe_repr(app, 200)))
            return False
    except Exception:
        pass

    if is_battle_queue_context():
        return False

    return True


def has_hangar_vehicle():
    current_vehicle = get_current_vehicle()
    if current_vehicle is None:
        log("not hangar: CurrentVehicle unavailable")
        return False

    try:
        if hasattr(current_vehicle, "isPresent"):
            if not current_vehicle.isPresent():
                log("not hangar: no selected vehicle")
                return False
    except Exception:
        log_exception("hangar vehicle isPresent")
        return False

    try:
        if getattr(current_vehicle, "item", None) is None:
            log("not hangar: no current vehicle item")
            return False
    except Exception:
        log_exception("hangar vehicle item")
        return False

    return True


def is_battle_queue_context():
    current_vehicle = get_current_vehicle()
    if current_vehicle is None:
        return False

    blocked_checks = [
        "isAwaitingBattle",
        "isInPrebattle",
        "isInUnit",
        "isInUnitFunctional",
        "isInBattleQueue",
        "isInQueue",
        "isWaitingForBattle"
    ]

    for method_name in blocked_checks:
        try:
            if hasattr(current_vehicle, method_name) and getattr(current_vehicle, method_name)():
                log("not hangar: vehicle {}".format(method_name))
                return True
        except Exception:
            log_exception("vehicle queue check {}".format(method_name))

    return False


def current_vehicle_allows_reset():
    current_vehicle = get_current_vehicle()
    if current_vehicle is None:
        log("vehicle guard: CurrentVehicle unavailable")
        return False

    try:
        if hasattr(current_vehicle, "isPresent") and not current_vehicle.isPresent():
            log("vehicle guard: no selected vehicle")
            return False
    except Exception:
        log_exception("vehicle guard isPresent")
        return False

    blocked_checks = [
        "isInBattle",
        "isAwaitingBattle",
        "isInPrebattle"
    ]

    for method_name in blocked_checks:
        try:
            if hasattr(current_vehicle, method_name) and getattr(current_vehicle, method_name)():
                log("vehicle guard: blocked by {}".format(method_name))
                return False
        except Exception:
            log_exception("vehicle guard {}".format(method_name))
            return False

    try:
        if hasattr(current_vehicle, "isReadyToFight") and not current_vehicle.isReadyToFight():
            log("vehicle guard: blocked by isReadyToFight=False")
            return False
    except Exception:
        log_exception("vehicle guard isReadyToFight")
        return False

    try:
        vehicle = current_vehicle.item
        log("vehicle guard OK: {}".format(safe_repr(vehicle, 300)))
    except Exception:
        log("vehicle guard OK")
    return True


def get_reset_button_status(quest_id, verbose=True):
    try:
        from gui.impl.gen.view_models.views.lobby.personal_missions.pm3_quest_model import Pm3QuestModel
        from gui.impl.lobby.personal_missions.personal_missions_quest_model import QuestModelParser

        quest_model = Pm3QuestModel()
        parser = QuestModelParser()
        parser.updateQuestModelFromID(quest_id, quest_model, {})
        status = quest_model.getResetButtonStatus()
        if verbose:
            log("quest {} resetButtonStatus={}".format(quest_id, safe_repr(status)))
        return status
    except Exception:
        log_exception("get_reset_button_status({})".format(quest_id))
        return None


def is_enabled_status(status):
    try:
        if status is None:
            return False
        value = getattr(status, "value", None)
        if value is not None:
            return str(value).lower() == "enabled"
        name = getattr(status, "name", None)
        if name is not None:
            return str(name).lower() == "enabled"
        text = str(status).lower()
        return text == "enabled" or text.endswith(".enabled")
    except Exception:
        return False


def is_reset_button_enabled(quest_id):
    return is_enabled_status(get_reset_button_status(quest_id, True))


def is_quest_available(quest):
    try:
        available = quest.isAvailable()
        return bool(getattr(available, "isValid", False))
    except Exception:
        return True


def progress_value_present(progress_item):
    try:
        if isinstance(progress_item, dict):
            for key in ["value", "count", "current", "progress"]:
                value = progress_item.get(key, 0)
                if isinstance(value, (int, long, float)) and value != 0:
                    return True
            battles = progress_item.get("battles", [])
            if battles:
                return True
            return False
        if isinstance(progress_item, (int, long, float)):
            return progress_item != 0
    except Exception:
        pass
    return False


def get_progress_info(quest):
    try:
        progress = call(quest, "getConditionsProgress", {})
        if not progress:
            return {"count": 0, "has": False}

        try:
            items = progress.iteritems()
        except Exception:
            try:
                items = progress.items()
            except Exception:
                items = []

        count = 0
        has_progress = False
        for _, progress_item in items:
            count += 1
            if progress_value_present(progress_item):
                has_progress = True
        return {"count": count, "has": has_progress}
    except Exception:
        log_exception("get_progress_info")
        return {"count": 0, "has": False}


def can_reset_quest(quest, quest_id, reset_status=None, progress_info=None):
    try:
        if quest is None:
            return False
        if not is_quest_available(quest):
            return False
        if not call_bool(quest, "isInProgress"):
            return False
        if call_bool(quest, "isDisabled"):
            return False
        if call_bool(quest, "isFullCompleted"):
            return False

        if reset_status is None:
            reset_status = get_reset_button_status(quest_id, False)
        if is_enabled_status(reset_status):
            return True

        if progress_info is None:
            progress_info = get_progress_info(quest)
        return bool(progress_info.get("has"))
    except Exception:
        log_exception("can_reset_quest({})".format(quest_id))
        return False


def can_reset_quest_id(quest_id):
    controller = get_controller()
    if controller is None:
        return False
    try:
        quest = controller.getQuest(quest_id)
    except Exception:
        log_exception("controller.getQuest({})".format(quest_id))
        return False
    return can_reset_quest(quest, quest_id, get_reset_button_status(quest_id, True), None)


def get_quest_id(quest, fallback):
    for method_name in ["getID", "getQuestID", "getGeneralQuestID"]:
        value = call(quest, method_name, None)
        if value is not None:
            return value
    return fallback


def get_quest_name(quest):
    short_name = first_text_method(quest, [
        "getShortUserName",
        "getShortName",
        "getUserName",
        "getName"
    ])
    title = first_text_method(quest, [
        "getFullUserName",
        "getUserFullName",
        "getTitle",
        "getUserTitle",
        "getDescription",
        "getUserDescription",
        "getName"
    ])
    try:
        if short_name and title:
            short_lower = short_name.lower()
            title_lower = title.lower()
            if short_lower == title_lower or title_lower.startswith(short_lower):
                return title
            return u"{} - {}".format(short_name, title)
        return short_name or title
    except Exception:
        log_exception("get_quest_name format")
        return short_name or title or u""


def iter_values(mapping):
    if mapping is None:
        return []
    try:
        return list(mapping.itervalues())
    except Exception:
        pass
    try:
        return list(mapping.values())
    except Exception:
        pass
    try:
        return list(mapping)
    except Exception:
        return []


def get_all_quests(controller):
    for method_name in ["getAllQuestsPM3", "getAllQuests"]:
        try:
            if hasattr(controller, method_name):
                quests = getattr(controller, method_name)()
                if quests:
                    log("{} returned {}".format(method_name, len(iter_values(quests))))
                    return quests
        except Exception:
            log_exception(method_name)
    return {}


def get_active_quests():
    controller = get_controller()
    if controller is None:
        return []

    quests = []
    all_quests = get_all_quests(controller)
    total_count = 0
    progress_count = 0
    disabled_count = 0
    full_completed_count = 0
    completed_count = 0
    reset_disabled_count = 0

    try:
        items = all_quests.iteritems()
    except Exception:
        try:
            items = all_quests.items()
        except Exception:
            items = []

    for key, quest in items:
        try:
            total_count += 1
            if not call_bool(quest, "isInProgress"):
                continue
            progress_count += 1
            is_final = call_bool(quest, "isFinal")
            is_completed = call_bool(quest, "isCompleted")
            if is_completed:
                completed_count += 1
            if call_bool(quest, "isFullCompleted") and not is_final:
                full_completed_count += 1
                continue
            if call_bool(quest, "isDisabled"):
                disabled_count += 1
                continue

            quest_id = get_quest_id(quest, key)
            reset_status = get_reset_button_status(quest_id, False)
            quest_progress = get_progress_info(quest)
            can_reset = can_reset_quest(quest, quest_id, reset_status, quest_progress)
            log("inProgress: id={} key={} completed={} fullCompleted={} final={} reset={} progressCount={} hasProgress={} name={}".format(
                quest_id,
                key,
                is_completed,
                call_bool(quest, "isFullCompleted"),
                is_final,
                safe_repr(reset_status, 120),
                quest_progress.get("count"),
                quest_progress.get("has"),
                safe_repr(get_quest_name(quest), 160)
            ))
            if not can_reset:
                reset_disabled_count += 1
                continue

            quests.append({
                "id": quest_id,
                "key": key,
                "name": get_quest_name(quest),
                "levels": get_quest_vehicle_levels(quest),
                "operation": call(quest, "getOperationID", None),
                "chain": call(quest, "getChainID", None),
                "branch": call(quest, "getQuestBranch", None),
                "final": is_final,
                "completed": is_completed,
                "resetStatus": reset_status,
                "progress": quest_progress
            })
        except Exception:
            log_exception("scan quest {}".format(safe_repr(key)))

    log("quest scan: total={} inProgress={} completed={} fullCompletedSkip={} disabled={} resetSkipped={} resetCandidates={}".format(
        total_count,
        progress_count,
        completed_count,
        full_completed_count,
        disabled_count,
        reset_disabled_count,
        len(quests)
    ))
    return quests


def make_task_label(quest):
    try:
        name = quest.get("name") or ""
        marker = u""
        if quest.get("locked"):
            marker = u" [locked]"
        return u"{}{}".format(
            name,
            marker
        )
    except Exception:
        return safe_repr(quest, 160)


def make_overlay_task_label(index, quest):
    try:
        status = u"[X]" if quest.get("locked") else u"[>]"
        name = trim_text(quest.get("name") or u"", 72)
        levels = trim_text(quest.get("levels") or u"", 20)
        if levels:
            return u"{}  {} {}".format(status, name, levels)
        return u"{}  {}".format(status, name)
    except Exception:
        return safe_repr(quest, 120)


def is_mouse_down_event(event):
    try:
        for method_name in ["isKeyDown", "isButtonDown", "isDown"]:
            method = getattr(event, method_name, None)
            if method is not None:
                return bool(method())
    except Exception:
        pass
    return True


class OverlayHoverScript(object):

    def __init__(self, action, index=None):
        self.action = action
        self.index = index

    def handleMouseEnterEvent(self, *args):
        global OVERLAY_HOVER_ACTION
        global OVERLAY_HOVER_INDEX
        global OVERLAY_HOVER_START_TIME
        global OVERLAY_HELP_SHOWN
        try:
            component = args[0] if args else None
            component.colour = (255, 255, 255, 255)
            OVERLAY_HOVER_ACTION = self.action
            OVERLAY_HOVER_INDEX = self.index
            OVERLAY_HOVER_START_TIME = time.time()
            OVERLAY_HELP_SHOWN = False
        except Exception:
            pass
        return True

    def handleMouseLeaveEvent(self, *args):
        global OVERLAY_HOVER_ACTION
        global OVERLAY_HOVER_INDEX
        global OVERLAY_HOVER_START_TIME
        global OVERLAY_HELP_SHOWN
        try:
            component = args[0] if args else None
            component.colour = (255, 235, 120, 255)
            if OVERLAY_HOVER_ACTION == self.action and OVERLAY_HOVER_INDEX == self.index:
                OVERLAY_HOVER_ACTION = None
                OVERLAY_HOVER_INDEX = None
                OVERLAY_HOVER_START_TIME = 0.0
                OVERLAY_HELP_SHOWN = False
        except Exception:
            pass
        return True


def notify(message):
    log(message)
    try:
        from gui import SystemMessages
        msg_type = None
        try:
            msg_type = SystemMessages.SM_TYPE.Information
        except Exception:
            pass

        try:
            lines = unicode(message).splitlines()
        except Exception:
            lines = [safe_repr(message, 500)]

        for line in lines:
            if not line:
                continue
            try:
                if msg_type is not None:
                    SystemMessages.pushMessage(line, type=msg_type)
                else:
                    SystemMessages.pushMessage(line)
            except Exception:
                log_exception("SystemMessages.pushMessage")
    except Exception:
        log_exception("notify")


def clamp(value, min_value, max_value):
    try:
        return max(min_value, min(max_value, value))
    except Exception:
        return min_value


def load_overlay_pos():
    try:
        if not os.path.exists(POS_FILE):
            return
        data = open(POS_FILE, "rb").read().strip()
        parts = data.split(",")
        if len(parts) != 2:
            return
        OVERLAY_POS["x"] = clamp(float(parts[0]), -0.95, 0.75)
        OVERLAY_POS["y"] = clamp(float(parts[1]), -0.75, 0.82)
        log("overlay pos loaded x={} y={}".format(OVERLAY_POS["x"], OVERLAY_POS["y"]))
    except Exception:
        log_exception("load_overlay_pos")


def save_overlay_pos():
    try:
        ensure_config_dir()
        with open(POS_FILE, "wb") as file_obj:
            file_obj.write("{:.3f},{:.3f}".format(OVERLAY_POS["x"], OVERLAY_POS["y"]))
        log("overlay pos saved x={} y={}".format(OVERLAY_POS["x"], OVERLAY_POS["y"]))
    except Exception:
        log_exception("save_overlay_pos")


def clear_overlay():
    global OVERLAY_COMPONENTS
    global OVERLAY_META
    global OVERLAY_DRAGGING
    global OVERLAY_SCRIPTS
    global OVERLAY_HOVER_ACTION
    global OVERLAY_HOVER_INDEX
    global OVERLAY_HOVER_START_TIME
    global OVERLAY_HELP_SHOWN
    if not OVERLAY_COMPONENTS:
        return
    try:
        import GUI
        for component in OVERLAY_COMPONENTS:
            try:
                GUI.delRoot(component)
            except Exception:
                pass
    except Exception:
        log_exception("clear_overlay")
    OVERLAY_COMPONENTS = []
    OVERLAY_META = []
    OVERLAY_SCRIPTS = []
    OVERLAY_DRAGGING = False
    OVERLAY_HOVER_ACTION = None
    OVERLAY_HOVER_INDEX = None
    OVERLAY_HOVER_START_TIME = 0.0
    OVERLAY_HELP_SHOWN = False


def show_overlay(lines, ttl=None):
    global OVERLAY_COMPONENTS
    global OVERLAY_META
    global OVERLAY_LINES
    global OVERLAY_SCRIPTS
    try:
        import GUI
        clear_overlay()
        OVERLAY_LINES = list(lines)
        x = OVERLAY_POS["x"]
        y = OVERLAY_POS["y"]
        line_count = min(len(lines), 12)

        try:
            background = None
            if hasattr(GUI, "Window"):
                background = GUI.Window("")
            elif hasattr(GUI, "Simple"):
                background = GUI.Simple("")
            if background is not None:
                background.horizontalAnchor = "LEFT"
                background.verticalAnchor = "TOP"
                background.position = (x - 0.025, y + 0.035, 0.95)
                background.width = 0.42
                background.height = line_count * OVERLAY_STEP + 0.035
                background.colour = (0, 0, 0, 135)
                background.visible = True
                GUI.addRoot(background)
                OVERLAY_COMPONENTS.append(background)
                OVERLAY_META.append({"kind": "background"})
        except Exception:
            log_exception("overlay background")

        for index, line_info in enumerate(lines[:12]):
            try:
                line = line_info.get("text")
                action = line_info.get("action")
                action_index = line_info.get("index")
                colour = line_info.get("colour", (255, 235, 120, 255))
                font = line_info.get("font", "default_medium.font")
                width = line_info.get("width", 0.40)
            except Exception:
                line = line_info
                action = None
                action_index = None
                colour = (255, 235, 120, 255)
                font = "default_medium.font"
                width = 0.40
            text = GUI.Text(line)
            try:
                text.horizontalAnchor = "LEFT"
                text.verticalAnchor = "TOP"
                text.position = (x, y - index * OVERLAY_STEP, 1.0)
                text.colour = colour
                text.visible = True
                text.multiline = False
                text.font = font
            except Exception:
                pass
            try:
                text.width = width
                text.height = 0.052
            except Exception:
                pass
            try:
                if action is not None:
                    text.mouseButtonFocus = True
                    text.moveFocus = True
                    text.crossFocus = True
                    text.focus = True
                    script = OverlayHoverScript(action, action_index)
                    text.script = script
                    OVERLAY_SCRIPTS.append(script)
            except Exception:
                log_exception("assign overlay hover script")
            GUI.addRoot(text)
            OVERLAY_COMPONENTS.append(text)
            OVERLAY_META.append({"kind": "text", "line": index})
        if BigWorld is not None:
            start_overlay_poll()
        log("overlay shown lines={}".format(len(OVERLAY_COMPONENTS)))
        return True
    except Exception:
        log_exception("show_overlay")
        clear_overlay()
        return False


def move_overlay(dx, dy):
    try:
        if not OVERLAY_COMPONENTS:
            return False
        OVERLAY_POS["x"] = clamp(OVERLAY_POS["x"] + dx, -0.95, 0.75)
        OVERLAY_POS["y"] = clamp(OVERLAY_POS["y"] + dy, -0.75, 0.82)
        for index, component in enumerate(OVERLAY_COMPONENTS):
            try:
                meta = OVERLAY_META[index] if index < len(OVERLAY_META) else {"kind": "text", "line": index}
                if meta.get("kind") == "background":
                    component.position = (OVERLAY_POS["x"] - 0.025, OVERLAY_POS["y"] + 0.035, 0.95)
                else:
                    line_index = meta.get("line", index)
                    component.position = (OVERLAY_POS["x"], OVERLAY_POS["y"] - line_index * OVERLAY_STEP, 1.0)
            except Exception:
                pass
        save_overlay_pos()
        log("overlay moved dx={} dy={}".format(dx, dy))
        return True
    except Exception:
        log_exception("move_overlay")
        return False


def get_mouse_pos():
    global MOUSE_POS_ERROR_LOGGED
    try:
        import GUI
        cursor = None
        try:
            cursor = GUI.mcursor()
        except Exception:
            cursor = getattr(GUI, "mcursor", None)
        if cursor is None:
            return None

        pos = getattr(cursor, "position", None)
        if callable(pos):
            pos = pos()
        if pos is None:
            return None

        try:
            x = float(pos[0])
            y = float(pos[1])
        except Exception:
            x = float(getattr(pos, "x"))
            y = float(getattr(pos, "y"))

        if abs(x) > 1.5 or abs(y) > 1.5:
            try:
                width = float(getattr(BigWorld, "screenWidth")())
                height = float(getattr(BigWorld, "screenHeight")())
                x = x / width * 2.0 - 1.0
                y = 1.0 - y / height * 2.0
            except Exception:
                x = clamp(x, -0.95, 0.75)
                y = clamp(y, -0.75, 0.82)

        return {"x": clamp(x, -0.95, 0.75), "y": clamp(y, -0.75, 0.82)}
    except Exception:
        if not MOUSE_POS_ERROR_LOGGED:
            MOUSE_POS_ERROR_LOGGED = True
            log_exception("get_mouse_pos")
    return None


def is_left_mouse_down():
    return is_named_key_down([
        "KEY_LEFTMOUSE",
        "KEY_MOUSE0",
        "KEY_LEFTBUTTON",
        "KEY_LBUTTON",
        "KEY_MOUSE_LEFT"
    ])


def has_left_mouse_key():
    if Keys is None:
        return False
    try:
        for name in ["KEY_LEFTMOUSE", "KEY_MOUSE0", "KEY_LEFTBUTTON", "KEY_LBUTTON", "KEY_MOUSE_LEFT"]:
            if hasattr(Keys, name):
                return True
    except Exception:
        pass
    return False


def is_right_mouse_down():
    return is_named_key_down([
        "KEY_RIGHTMOUSE",
        "KEY_MOUSE1",
        "KEY_RIGHTBUTTON",
        "KEY_RBUTTON",
        "KEY_MOUSE_RIGHT"
    ])


def start_overlay_drag():
    global OVERLAY_DRAGGING
    global OVERLAY_DRAG_LAST_POS
    try:
        mouse = get_mouse_pos()
        OVERLAY_DRAGGING = True
        OVERLAY_DRAG_LAST_POS = mouse
        log("overlay drag started mouse={}".format(safe_repr(mouse, 120)))
        start_overlay_poll()
        return True
    except Exception:
        log_exception("start_overlay_drag")
        return True


def stop_overlay_drag():
    global OVERLAY_DRAGGING
    global OVERLAY_DRAG_LAST_POS
    try:
        if OVERLAY_DRAGGING:
            OVERLAY_DRAGGING = False
            OVERLAY_DRAG_LAST_POS = None
            save_overlay_pos()
            log("overlay drag stopped")
    except Exception:
        log_exception("stop_overlay_drag")
    return True


def poll_overlay_drag():
    global OVERLAY_DRAG_LAST_POS
    try:
        if not OVERLAY_DRAGGING:
            return False
        if has_left_mouse_key() and not is_left_mouse_down():
            stop_overlay_drag()
            return True
        mouse = get_mouse_pos()
        if mouse is None:
            return True
        if OVERLAY_DRAG_LAST_POS is None:
            OVERLAY_DRAG_LAST_POS = mouse
            return True
        dx = mouse["x"] - OVERLAY_DRAG_LAST_POS["x"]
        dy = mouse["y"] - OVERLAY_DRAG_LAST_POS["y"]
        OVERLAY_DRAG_LAST_POS = mouse
        if abs(dx) > 0.001 or abs(dy) > 0.001:
            move_overlay(dx, dy)
        return True
    except Exception:
        log_exception("poll_overlay_drag")
        return True


def is_named_key_down(names):
    if BigWorld is None or Keys is None:
        return False
    try:
        for name in names:
            if hasattr(Keys, name) and BigWorld.isKeyDown(getattr(Keys, name)):
                return True
    except Exception:
        log_exception("is_named_key_down")
    return False


def is_ctrl_down():
    return is_named_key_down([
        "KEY_LCONTROL",
        "KEY_RCONTROL",
        "KEY_LCTRL",
        "KEY_RCTRL",
        "KEY_CONTROL",
        "KEY_CTRL"
    ])


def is_alt_down():
    return is_named_key_down([
        "KEY_LALT",
        "KEY_RALT",
        "KEY_ALT",
        "KEY_LMENU",
        "KEY_RMENU"
    ])


def set_overlay_position(x, y, save_now=False):
    global LAST_OVERLAY_SAVE_TIME
    try:
        if not OVERLAY_COMPONENTS:
            return False
        OVERLAY_POS["x"] = clamp(x, -0.95, 0.75)
        OVERLAY_POS["y"] = clamp(y, -0.75, 0.82)
        for index, component in enumerate(OVERLAY_COMPONENTS):
            try:
                meta = OVERLAY_META[index] if index < len(OVERLAY_META) else {"kind": "text", "line": index}
                if meta.get("kind") == "background":
                    component.position = (OVERLAY_POS["x"] - 0.025, OVERLAY_POS["y"] + 0.035, 0.95)
                else:
                    line_index = meta.get("line", index)
                    component.position = (OVERLAY_POS["x"], OVERLAY_POS["y"] - line_index * OVERLAY_STEP, 1.0)
            except Exception:
                pass
        now = time.time()
        if save_now or now - LAST_OVERLAY_SAVE_TIME > 0.8:
            LAST_OVERLAY_SAVE_TIME = now
            save_overlay_pos()
        return True
    except Exception:
        log_exception("set_overlay_position")
        return False


def get_first_ready_selector_index():
    try:
        for index, quest in enumerate(SELECTOR_QUESTS):
            if not quest.get("locked"):
                return index
    except Exception:
        log_exception("get_first_ready_selector_index")
    return None


def maybe_show_overlay_help(now):
    global OVERLAY_HELP_SHOWN
    try:
        if OVERLAY_HELP_SHOWN:
            return
        if OVERLAY_HOVER_ACTION is None:
            return
        if OVERLAY_HOVER_START_TIME <= 0.0:
            return
        if now - OVERLAY_HOVER_START_TIME < 0.9:
            return
        OVERLAY_HELP_SHOWN = True
        notify(OVERLAY_HELP_TEXT)
    except Exception:
        log_exception("maybe_show_overlay_help")


def poll_overlay_keys():
    global LAST_OVERLAY_MOVE_TIME
    global LAST_OVERLAY_SELECT_TIME
    global LAST_MOUSE_ACTION_TIME

    try:
        if not OVERLAY_COMPONENTS:
            return
        if not is_hangar_context():
            log("overlay cleared outside hangar")
            clear_overlay()
            return

        if poll_overlay_drag():
            return

        now = time.time()
        maybe_show_overlay_help(now)

        if is_ctrl_down() and is_left_mouse_down():
            mouse = get_mouse_pos()
            if mouse is not None:
                set_overlay_position(mouse["x"], mouse["y"])
                return

        if (not is_ctrl_down()) and is_left_mouse_down() and OVERLAY_HOVER_ACTION == "task":
            if now - LAST_MOUSE_ACTION_TIME > 0.35:
                LAST_MOUSE_ACTION_TIME = now
                select_overlay_index(OVERLAY_HOVER_INDEX, is_alt_down())
                return

        if is_named_key_down(["KEY_R"]) and now - LAST_OVERLAY_SELECT_TIME > 0.35:
            LAST_OVERLAY_SELECT_TIME = now
            ready_index = get_first_ready_selector_index()
            if ready_index is None:
                notify(u"LBZ Reset: no ready task")
            else:
                select_overlay_index(ready_index, is_alt_down())
    except Exception:
        log_exception("poll_overlay_keys")


def overlay_poll_loop():
    global OVERLAY_POLL_RUNNING
    try:
        if not OVERLAY_COMPONENTS:
            OVERLAY_POLL_RUNNING = False
            return
        poll_overlay_keys()
    except Exception:
        log_exception("overlay_poll_loop")

    try:
        if BigWorld is not None:
            BigWorld.callback(0.1, overlay_poll_loop)
    except Exception:
        OVERLAY_POLL_RUNNING = False


def start_overlay_poll():
    global OVERLAY_POLL_RUNNING
    try:
        if OVERLAY_POLL_RUNNING or BigWorld is None:
            return
        OVERLAY_POLL_RUNNING = True
        BigWorld.callback(0.1, overlay_poll_loop)
        log("overlay poll started")
    except Exception:
        OVERLAY_POLL_RUNNING = False
        log_exception("start_overlay_poll")


def select_overlay_index(index, direct_reset=False):
    global SELECTOR_QUESTS
    global SELECTOR_UNTIL

    try:
        if not SELECTOR_QUESTS or time.time() > SELECTOR_UNTIL:
            log("select_overlay_index ignored: selector inactive")
            return True
        if index < 0 or index >= len(SELECTOR_QUESTS):
            notify(u"LBZ Reset: no task on this number")
            return True

        quest = SELECTOR_QUESTS[index]
        quest_id = quest.get("id")
        if direct_reset and quest.get("locked"):
            notify(u"LBZ Reset: task is locked {}".format(make_task_label(quest)))
            return True
        if direct_reset:
            notify(u"LBZ Reset: direct reset {}".format(make_task_label(quest)))
            open_reset_dialog(quest_id)
            return True
        notify(u"LBZ Reset: opening card {}".format(make_task_label(quest)))
        open_quest_card(quest_id)
        return True
    except Exception:
        log_exception("select_overlay_index({}, {})".format(index, direct_reset))
        return True


def handle_overlay_click(action, index):
    try:
        if action == "drag":
            if OVERLAY_DRAGGING:
                return stop_overlay_drag()
            return start_overlay_drag()
        if action == "task":
            return select_overlay_index(index, is_alt_down())
        if action == "left":
            return move_overlay(-OVERLAY_MOVE_STEP, 0.0)
        if action == "right":
            return move_overlay(OVERLAY_MOVE_STEP, 0.0)
        if action == "up":
            return move_overlay(0.0, OVERLAY_MOVE_STEP)
        if action == "down":
            return move_overlay(0.0, -OVERLAY_MOVE_STEP)
        if action == "resetpos":
            OVERLAY_POS["x"] = 0.22
            OVERLAY_POS["y"] = 0.35
            save_overlay_pos()
            return move_overlay(0.0, 0.0)
    except Exception:
        log_exception("handle_overlay_click")
    return True


def show_info_dialog(title, message):
    try:
        from gui.impl.dialogs import dialogs
        from gui.impl.dialogs.builders import InfoDialogBuilder

        builder = InfoDialogBuilder()
        if hasattr(builder, "setTitle"):
            builder.setTitle(title)
        if hasattr(builder, "setFormattedMessage"):
            builder.setFormattedMessage(message)
        if hasattr(builder, "setConfirmButtonLabel"):
            builder.setConfirmButtonLabel(u"OK")
        dialogs.showSimple(builder.build())
        log("info dialog shown: {}".format(safe_repr(title, 120)))
        return True
    except Exception:
        log_exception("show_info_dialog")
        return False


def get_selector_quests():
    controller = get_controller()
    if controller is None:
        return []

    result = []
    all_quests = get_all_quests(controller)
    try:
        items = all_quests.iteritems()
    except Exception:
        try:
            items = all_quests.items()
        except Exception:
            items = []

    for key, quest in items:
        try:
            if not call_bool(quest, "isInProgress"):
                continue
            quest_id = get_quest_id(quest, key)
            reset_status = get_reset_button_status(quest_id, False)
            progress_info = get_progress_info(quest)
            can_reset = can_reset_quest(quest, quest_id, reset_status, progress_info)
            result.append({
                "id": quest_id,
                "key": key,
                "name": get_quest_name(quest),
                "levels": get_quest_vehicle_levels(quest),
                "operation": call(quest, "getOperationID", None),
                "chain": call(quest, "getChainID", None),
                "branch": call(quest, "getQuestBranch", None),
                "final": call_bool(quest, "isFinal"),
                "completed": call_bool(quest, "isCompleted"),
                "resetStatus": reset_status,
                "progress": progress_info,
                "locked": not can_reset
            })
        except Exception:
            log_exception("selector scan quest {}".format(safe_repr(key)))

    log("selector quests count={}".format(len(result)))
    return result


def get_digit_key_index(key):
    if Keys is None:
        return None
    try:
        key_map = [
            ("KEY_1", 0), ("KEY_2", 1), ("KEY_3", 2),
            ("KEY_4", 3), ("KEY_5", 4), ("KEY_6", 5),
            ("KEY_7", 6), ("KEY_8", 7), ("KEY_9", 8)
        ]
        for key_name, index in key_map:
            if hasattr(Keys, key_name) and key == getattr(Keys, key_name):
                return index
    except Exception:
        log_exception("get_digit_key_index")
    return None


def key_matches(key, names):
    if Keys is None:
        return False
    try:
        for name in names:
            if hasattr(Keys, name) and key == getattr(Keys, name):
                return True
    except Exception:
        log_exception("key_matches")
    return False


def handle_overlay_move_key(key):
    return False


def show_task_selector(reason):
    global SELECTOR_QUESTS
    global SELECTOR_UNTIL

    try:
        if not is_hangar_context():
            log("selector not shown outside hangar: {}".format(reason))
            clear_overlay()
            return False

        quests = get_selector_quests()[:9]
        SELECTOR_QUESTS = quests
        SELECTOR_UNTIL = time.time() + 86400.0

        if not quests:
            notify(u"LBZ Reset: no current LBZ tasks")
            return False

        lines = [
            {
                "text": OVERLAY_TITLE,
                "font": "default_large.font",
                "colour": (255, 214, 60, 255),
                "width": 0.34,
                "action": "help"
            }
        ]
        for index, quest in enumerate(quests):
            colour = (255, 240, 80, 255)
            if quest.get("locked"):
                colour = (185, 190, 198, 215)
            lines.append({
                "text": make_overlay_task_label(index, quest),
                "font": "default_medium.font",
                "colour": colour,
                "width": 0.38,
                "action": "task",
                "index": index
            })

        message = u"\n".join([line.get("text") for line in lines])
        log("selector shown [{}]: {}".format(reason, safe_repr(message, 1200)))
        if not show_overlay(lines) and not show_info_dialog(u"LBZ Reset", message):
            notify(message)
        return True
    except Exception:
        log_exception("show_task_selector({})".format(reason))
        return False


def restore_overlay_if_needed(reason):
    try:
        if not OVERLAY_WANTED:
            return False
        if OVERLAY_COMPONENTS:
            return False
        if not is_hangar_context():
            return False
        log("restore overlay: {}".format(reason))
        return show_task_selector(reason)
    except Exception:
        log_exception("restore_overlay_if_needed({})".format(reason))
        return False


def refresh_overlay(reason):
    try:
        if not OVERLAY_COMPONENTS:
            return False
        if not is_hangar_context():
            return False
        log("refresh overlay: {}".format(reason))
        return show_task_selector(reason)
    except Exception:
        log_exception("refresh_overlay({})".format(reason))
        return False


def handle_selector_key(key):
    try:
        index = get_digit_key_index(key)
        if index is None:
            return False
        if not SELECTOR_QUESTS or time.time() > SELECTOR_UNTIL:
            return False
        return select_overlay_index(index, is_alt_down())
    except Exception:
        log_exception("handle_selector_key")
        return False


def build_settings_template():
    try:
        from gui.modsSettingsApi import templates
    except Exception:
        log_exception("import modsSettingsApi.templates")
        return None

    column = []
    column.append(templates.createLabel(
        u"РђРєС‚РёРІРЅС‹Рµ Р·Р°РґР°С‡Рё Р›Р‘Р— РґР»СЏ СЃР±СЂРѕСЃР°",
        u"F9 РѕС‚РєСЂС‹РІР°РµС‚ СЌС‚Рѕ РѕРєРЅРѕ. РќР°Р¶РёРјР°Р№ РєРЅРѕРїРєСѓ СЂСЏРґРѕРј СЃ Р·Р°РґР°С‡РµР№.",
        None
    ))
    column.append(templates.createCheckbox(
        u"РћР±РЅРѕРІРёС‚СЊ СЃРїРёСЃРѕРє",
        "refresh",
        False,
        u"РџРµСЂРµСЃРєР°РЅРёСЂРѕРІР°С‚СЊ Р°РєС‚РёРІРЅС‹Рµ Р·Р°РґР°С‡Рё.",
        None,
        templates.createButton(150, 24, u"РћР±РЅРѕРІРёС‚СЊ", None, None, None, None, None)
    ))

    quests = get_active_quests()
    if not quests:
        column.append(templates.createLabel(
            u"РќРµС‚ Р·Р°РґР°С‡, РєРѕС‚РѕСЂС‹Рµ СЃРµР№С‡Р°СЃ РјРѕР¶РЅРѕ СЃР±СЂРѕСЃРёС‚СЊ.",
            u"Р•СЃР»Рё РєР»РёРµРЅС‚ РµС‰Рµ РіСЂСѓР·РёС‚ Р›Р‘Р—, РЅР°Р¶РјРё РћР±РЅРѕРІРёС‚СЊ С‡РµСЂРµР· РїР°СЂСѓ СЃРµРєСѓРЅРґ.",
            None
        ))
    else:
        for index, quest in enumerate(quests[:MAX_SETTINGS_ROWS]):
            quest_id = quest.get("id")
            column.append(templates.createCheckbox(
                make_task_label(quest),
                "reset_{}".format(quest_id),
                False,
                u"РЎР±СЂРѕСЃРёС‚СЊ С‡РµСЂРµР· С€С‚Р°С‚РЅРѕРµ РѕРєРЅРѕ РїРѕРґС‚РІРµСЂР¶РґРµРЅРёСЏ.",
                None,
                templates.createButton(150, 24, u"РЎР±СЂРѕСЃРёС‚СЊ", None, None, None, None, None)
            ))

    return {
        "modDisplayName": SETTINGS_TITLE,
        "settingsVersion": MOD_VERSION,
        "enabled": True,
        "column1": column,
        "column2": []
    }


def update_settings_template(register_callbacks=False):
    global SETTINGS_REGISTERED
    try:
        from gui.modsSettingsApi import g_modsSettingsApi
        template = build_settings_template()
        if template is None:
            return False

        if register_callbacks and not SETTINGS_REGISTERED:
            g_modsSettingsApi.setModTemplate(
                SETTINGS_LINKAGE,
                template,
                on_settings_changed,
                on_settings_button
            )
            SETTINGS_REGISTERED = True
            log("ModsSettingsAPI template registered")
            return True

        g_modsSettingsApi.activeMods.add(SETTINGS_LINKAGE)
        g_modsSettingsApi.state["templates"][SETTINGS_LINKAGE] = template
        g_modsSettingsApi.state["settings"][SETTINGS_LINKAGE] = g_modsSettingsApi.getSettingsFromTemplate(template)
        log("ModsSettingsAPI template refreshed")
        return True
    except Exception:
        log_exception("update_settings_template")
        return False


def on_settings_changed(linkage, settings):
    if linkage != SETTINGS_LINKAGE:
        return
    log("settings changed {}".format(safe_repr(settings, 300)))


def on_settings_button(linkage, var_name, value):
    try:
        if linkage != SETTINGS_LINKAGE:
            return
        log("settings button: var={} value={}".format(var_name, safe_repr(value, 120)))

        if var_name == "refresh":
            update_settings_template(False)
            notify(u"LBZ Reset: СЃРїРёСЃРѕРє РѕР±РЅРѕРІР»РµРЅ")
            return

        if var_name.startswith("reset_"):
            quest_id = int(var_name.split("_", 1)[1])
            notify(u"LBZ Reset: opening card {}".format(quest_id))
            open_quest_card(quest_id)
            return
    except Exception:
        log_exception("on_settings_button")


def on_settings_window_opened():
    update_settings_template(False)


def open_settings_window():
    try:
        if not update_settings_template(False):
            return False
        from gui.modsSettingsApi import g_modsSettingsApi
        from gui.modsSettingsApi.view import loadView
        log("open ModsSettingsAPI window")
        loadView(g_modsSettingsApi)
        return True
    except Exception:
        log_exception("open_settings_window")
        return False


def finish_reset_flow(reason):
    global RESET_IN_PROGRESS
    RESET_IN_PROGRESS = False
    log("reset flow finished: {}".format(reason))
    try:
        if BigWorld is not None:
            BigWorld.callback(1.0, lambda: refresh_overlay("reset finished"))
    except Exception:
        log_exception("schedule refresh after reset")


def get_quest_for_card(quest_id):
    try:
        controller = get_controller()
        if controller is None:
            log("open card blocked: controller unavailable")
            return None
        quest = controller.getQuest(quest_id)
        if quest is None:
            log("open card blocked: quest unavailable {}".format(quest_id))
            return None
        return quest
    except Exception:
        log_exception("get_quest_for_card({})".format(quest_id))
        return None


def call_open_quest_card(open_window, page_enum, operation_id, quest_id):
    attempts = [
        ("questId kw", lambda: open_window(page_enum.QUEST, operation_id, questId=quest_id)),
        ("questID kw", lambda: open_window(page_enum.QUEST, operation_id, questID=quest_id)),
        ("selectedQuestID kw", lambda: open_window(page_enum.QUEST, operation_id, selectedQuestID=quest_id)),
        ("ctx kw", lambda: open_window(page_enum.QUEST, operation_id, ctx={"questId": quest_id})),
        ("third arg", lambda: open_window(page_enum.QUEST, operation_id, quest_id)),
        ("quests page", lambda: open_window(page_enum.QUESTS, operation_id))
    ]

    for label, action in attempts:
        try:
            result = action()
            log("open quest card ok [{}] quest={} operation={} result={}".format(
                label,
                quest_id,
                operation_id,
                safe_repr(result, 160)
            ))
            return True
        except TypeError:
            log_exception("open quest card TypeError [{}]".format(label))
        except Exception:
            log_exception("open quest card failed [{}]".format(label))
    return False


def open_quest_card(quest_id):
    try:
        if not is_hangar_context():
            log("open quest card blocked: not hangar")
            return False

        quest = get_quest_for_card(quest_id)
        if quest is None:
            return False

        try:
            operation_id = quest.getOperationID()
        except Exception:
            log_exception("quest.getOperationID({})".format(quest_id))
            operation_id = None

        if operation_id is None:
            log("open quest card blocked: no operation id for {}".format(quest_id))
            return False

        from gui.impl.lobby.personal_missions.personal_missions_window_events import showPersonalMissionsOperationWindow
        from gui.impl.gen.view_models.views.lobby.personal_missions.personal_missions_main_quests_view_model import PageViewIdEnum

        log("open quest card request quest={} operation={}".format(quest_id, operation_id))
        if call_open_quest_card(showPersonalMissionsOperationWindow, PageViewIdEnum, operation_id, quest_id):
            return True

        try:
            from gui.server_events.events_dispatcher import showPersonalMissionsOperationsMap
            from personal_missions import PM_BRANCH
            showPersonalMissionsOperationsMap(PM_BRANCH.PERSONAL_MISSION_3)
            log("open quest card fallback: operations map")
            return True
        except Exception:
            log_exception("open quest card fallback map")
    except Exception:
        log_exception("open_quest_card({})".format(quest_id))
    return False


def run_pmdiscard(quest_id, finish_callback=None):
    try:
        from adisp import adisp_process
    except Exception:
        log_exception("import adisp_process")
        try:
            if finish_callback is not None:
                finish_callback("PMDiscard import error")
        except Exception:
            log_exception("PMDiscard import finish callback")
        return

    @adisp_process
    def discard_flow():
        try:
            from gui import SystemMessages
            from gui.shared.gui_items.processors import quests as quests_proc
            from personal_missions import PM_BRANCH

            if not can_reset_quest_id(quest_id):
                log("PMDiscard blocked: quest is not reset candidate {}".format(quest_id))
                return

            controller = get_controller()
            if controller is None:
                log("PMDiscard blocked: controller unavailable")
                return

            quest = controller.getQuest(quest_id)
            if quest is None:
                log("PMDiscard blocked: quest unavailable {}".format(quest_id))
                return

            log("PMDiscard request quest={}".format(quest_id))
            result = yield quests_proc.PMDiscard(quest, PM_BRANCH.PERSONAL_MISSION_3).request()
            log("PMDiscard result {}".format(safe_repr(result)))

            try:
                if result and result.userMsg:
                    SystemMessages.pushMessage(result.userMsg, type=result.sysMsgType)
            except Exception:
                log_exception("push PMDiscard message")
        except Exception:
            log_exception("discard_flow({})".format(quest_id))
        finally:
            try:
                if finish_callback is not None:
                    finish_callback("PMDiscard")
            except Exception:
                log_exception("PMDiscard finish callback")

    try:
        discard_flow()
    except Exception:
        log_exception("run_pmdiscard({})".format(quest_id))
        try:
            if finish_callback is not None:
                finish_callback("PMDiscard start error")
        except Exception:
            log_exception("PMDiscard start finish callback")


def is_submit_result(result):
    try:
        if result is True:
            return True
        text = str(result).lower()
        return text in ("submit", "ok", "confirm", "confirmed", "true") or text.endswith(".submit") or text.endswith(".ok")
    except Exception:
        return False


def run_reset_flow(quest_id):
    global RESET_IN_PROGRESS
    try:
        if RESET_IN_PROGRESS:
            log("run_reset_flow blocked: reset already in progress")
            return
        if not can_reset_quest_id(quest_id):
            log("confirm_flow blocked: quest is not reset candidate {}".format(quest_id))
            return

        RESET_IN_PROGRESS = True
        log("run PMDiscard flow with built-in confirmation for {}".format(quest_id))
        run_pmdiscard(quest_id, finish_reset_flow)
    except Exception:
        log_exception("run_reset_flow({})".format(quest_id))
        finish_reset_flow("start exception")


def open_reset_dialog(quest_id):
    try:
        if not can_reset_quest_id(quest_id):
            log("open_reset_dialog blocked: quest is not reset candidate {}".format(quest_id))
            return
        run_reset_flow(quest_id)
    except Exception:
        log_exception("open_reset_dialog({})".format(quest_id))


def open_reset_dialog_old(quest_id):
    try:
        from gui.shared import event_dispatcher
        log("showPMDiscardConfirmationDialog({})".format(quest_id))
        result = event_dispatcher.showPMDiscardConfirmationDialog(quest_id)
        log("dispatcher returned {}".format(safe_repr(result)))
    except Exception:
        log_exception("open_reset_dialog({})".format(quest_id))


def is_key_down(key_code):
    if BigWorld is None:
        return False
    try:
        return bool(BigWorld.isKeyDown(key_code))
    except Exception:
        return False


def handle_f9(source):
    global LAST_KEY_TIME
    global NEXT_INDEX
    global SELECTOR_QUESTS
    global SELECTOR_UNTIL
    global OVERLAY_WANTED

    try:
        if RESET_IN_PROGRESS:
            log("F9 ignored: reset already in progress")
            return
        if not is_hangar_context():
            log("F9 ignored: not hangar")
            clear_overlay()
            return

        now = time.time()
        if now - LAST_KEY_TIME < HOTKEY_COOLDOWN:
            return
        LAST_KEY_TIME = now
        if OVERLAY_COMPONENTS:
            log("F9: hide task selector")
            OVERLAY_WANTED = False
            SELECTOR_QUESTS = []
            SELECTOR_UNTIL = 0.0
            clear_overlay()
            return
        log("F9: show task selector")
        OVERLAY_WANTED = True
        show_task_selector("F9")
    except Exception:
        log_exception("handle_f9({})".format(source))


def get_event_key(event, args):
    for attr_name in ["key", "keyCode", "keyCodeValue"]:
        try:
            value = getattr(event, attr_name, None)
            if value is not None:
                return value
        except Exception:
            pass
    try:
        if args:
            value = args[0]
            if isinstance(value, (int, long)):
                return value
    except Exception:
        pass
    return None


def is_repeated_event(event):
    for method_name in ["isRepeatedEvent", "isRepeated", "isRepeat"]:
        try:
            method = getattr(event, method_name, None)
            if method is not None and method():
                return True
        except Exception:
            pass
    return False


def input_key_down_handler(event, *args):
    try:
        if Keys is None or not hasattr(Keys, "KEY_F9"):
            return
        key = get_event_key(event, args)
        if handle_overlay_move_key(key):
            return
        if key == Keys.KEY_F9:
            if is_repeated_event(event):
                return
            handle_f9("input")
            return
        if OVERLAY_COMPONENTS:
            log("overlay unhandled key={} event={} args={}".format(
                safe_repr(key, 80),
                safe_repr(event, 180),
                safe_repr(args, 180)
            ))
    except Exception:
        log_exception("input_key_down_handler")


def register_input_hook():
    global INPUT_HOOKED
    if INPUT_HOOKED:
        return
    try:
        from gui import InputHandler
        InputHandler.g_instance.onKeyDown += input_key_down_handler
        INPUT_HOOKED = True
        log("InputHandler onKeyDown hook registered")
    except Exception:
        log_exception("register_input_hook")


def disable_older_modules():
    try:
        current_module = sys.modules.get(__name__)
        for module_name in [
            "mod_lbz_dynamic_reset",
            "mod_lbz_dynamic_reset_fix",
            "mod_lbz_dynamic_reset_v006",
            "mod_lbz_dynamic_reset_v007",
            "mod_lbz_dynamic_reset_v008",
            "mod_lbz_dynamic_reset_v009",
            "mod_lbz_dynamic_reset_v010",
            "mod_lbz_dynamic_reset_v011",
            "mod_lbz_dynamic_reset_v012",
            "mod_lbz_dynamic_reset_v013",
            "mod_lbz_dynamic_reset_v014",
            "mod_lbz_dynamic_reset_v015",
            "mod_lbz_dynamic_reset_v016",
            "mod_lbz_dynamic_reset_v017",
            "mod_lbz_dynamic_reset_v018",
            "mod_lbz_dynamic_reset_v019",
            "mod_lbz_dynamic_reset_v020",
            "mod_lbz_dynamic_reset_v021",
            "mod_lbz_dynamic_reset_v022",
            "mod_lbz_dynamic_reset_v023",
            "mod_lbz_dynamic_reset_v024",
            "mod_lbz_dynamic_reset_v025",
            "mod_lbz_dynamic_reset_v026",
            "mod_lbz_dynamic_reset_v027",
            "mod_lbz_dynamic_reset_v028",
            "mod_lbz_dynamic_reset_v029",
            "mod_lbz_dynamic_reset_v030",
            "mod_lbz_dynamic_reset_v031",
            "mod_lbz_dynamic_reset_v032",
            "mod_lbz_dynamic_reset_v033",
            "mod_lbz_dynamic_reset_v034",
            "mod_lbz_dynamic_reset_v035",
            "mod_lbz_dynamic_reset_v036"
        ]:
            module = sys.modules.get(module_name)
            if module is None or module is current_module:
                continue
            if getattr(module, "MOD_NAME", "") != MOD_NAME:
                continue

            try:
                from gui import InputHandler
                old_handler = getattr(module, "input_key_down_handler", None)
                if old_handler is not None:
                    InputHandler.g_instance.onKeyDown -= old_handler
            except Exception:
                pass

            try:
                old_clear = getattr(module, "clear_overlay", None)
                if old_clear is not None:
                    old_clear()
            except Exception:
                pass

            try:
                module.handle_f9 = lambda *args, **kwargs: None
                module.key_poll_loop = lambda *args, **kwargs: None
            except Exception:
                pass
            log("disabled older loaded module {}".format(module_name))
    except Exception:
        log_exception("disable_older_modules")


def key_poll_loop():
    global LAST_POLL_DOWN
    global LAST_OVERLAY_REFRESH_TIME

    try:
        now = time.time()
        if not is_hangar_context():
            if OVERLAY_COMPONENTS:
                log("overlay cleared outside hangar")
                clear_overlay()
            try:
                if BigWorld is not None:
                    BigWorld.callback(5.0, key_poll_loop)
            except Exception:
                pass
            return

        restore_overlay_if_needed("periodic")
        if OVERLAY_COMPONENTS and now - LAST_OVERLAY_REFRESH_TIME > 5.0:
            LAST_OVERLAY_REFRESH_TIME = now
            refresh_overlay("periodic")

        # F9 is handled by InputHandler; this loop only restores/refreshes overlay.
    except Exception:
        log_exception("key_poll_loop")

    try:
        if BigWorld is not None:
            BigWorld.callback(5.0, key_poll_loop)
    except Exception:
        pass


def init():
    global INIT_DONE
    if INIT_DONE:
        return
    INIT_DONE = True

    try:
        load_overlay_pos()
        disable_older_modules()
        register_input_hook()
        if BigWorld is not None:
            BigWorld.callback(8.0, key_poll_loop)
        else:
            key_poll_loop()
    except Exception:
        log_exception("init")


init()
