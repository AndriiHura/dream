# %%
from typing import List
import types
import json
import pathlib
import os
import traceback

from utils.programy_extention import MindfulDataFileBot
from utils.programy_model import run_models, cmd_postprocessing
from utils.state import State

# configuration
STORAGE_PATH = os.getenv("STORAGE_PATH")
content_dir = pathlib.Path(os.getenv("CONTENT_PATH", "content"))


# load programy models
storage_path = pathlib.Path(STORAGE_PATH) if STORAGE_PATH else pathlib.Path(__file__).parent / "storage"

share_set_path = pathlib.Path("share_storage/sets")
category_pathes = list((storage_path).glob("./categories/*")) + list(
    pathlib.Path("share_storage").glob("./categories/*")
)
aiml_files = {
    category_path.name: {"aiml": [category_path], "sets": [share_set_path]} for category_path in category_pathes
}

# load content
latest_json_file = list(sorted(content_dir.glob("./*.json")))[-1]
tops = json.load(latest_json_file.open())
# init models
{model_name: print(files) for model_name, files in aiml_files.items()}
models = {model_name: MindfulDataFileBot(files) for model_name, files in aiml_files.items()}

# %%


skill_attrs = types.SimpleNamespace()
skill_attrs.skill_name = pathlib.Path(__file__).parent.name
skill_attrs.modes = types.SimpleNamespace()
skill_attrs.modes.intro = "intro"

month_d2s = {
    "01": "January",
    "02": "February",
    "03": "March",
    "04": "April",
    "05": "May",
    "06": "June",
    "07": "July",
    "08": "August",
    "09": "September",
    "10": "October",
    "11": "November",
    "12": "December",
}


def describe_top_handler(state, skill_state, true_model_names, true_cmds):
    confidence = 1.0
    scenario = True
    top = skill_state.get("top", [])
    top_name = skill_state.get("top_name", "")
    top_index = skill_state.get("top_index", 0)
    current_game = top[top_index]

    if "YES_ANSWER" in true_cmds or "NEXT_ANSWER" in true_cmds:
        state.add_content("games", current_game)
        if top_index == 0 and "name_original" in current_game:
            text = f"The game with the highest rating is {current_game.get('name_original')}. "
        else:
            text = f"The next game is {current_game.get('name_original')}. "

        # released
        if current_game.get("released"):
            try:
                year, month, day = current_game.get("released").split("-")
                text += f"It was released on {day} {month_d2s[month]} {year}. "
            except Exception:
                print(traceback.format_exc())

        # genres
        if current_game.get("genres"):
            try:
                genres = current_game.get("genres")
                genres = [genre["name"] for genre in genres]
                if len(genres) == 1:
                    text += f"It's {genres[0]}. "
                else:
                    genres = [", ".join(genres[:-2])] + [genres[-2]] + ["&"] + [genres[-1]]
                    genres = " ".join(genres)
                    text += f"It's a combination of {genres}. "
            except Exception:
                print(traceback.format_exc())

        # ratings
        if current_game.get("ratings"):
            try:
                rating = sorted(current_game.get("ratings"), key=lambda x: x["percent"])[-1]
                title = rating["title"]
                percent = int(rating["percent"])
                text += f"{percent} percent of people marked {current_game.get('name_original')} as {title}. "
            except Exception:
                print(traceback.format_exc())

        if len(top) - 1 != top_index:
            text += "If you want to discuss it in details say I want to talk about it. "
            "Otherwise we can always talk about other things."
            skill_state_update = {"next_step": "describe_top", "top_index": top_index + 1}
        else:
            if "previous_yearly_top" == top_name:
                text += "These are all the games from last year. "
            elif "yearly_top" == top_name:
                text += "These are all the games from this year. "
            elif "monthly_top" == top_name:
                text += "These are all the games from the past month. "
            elif "weekly_top" == top_name:
                text += "These are all the games from the past week. "
            else:
                text += "These are all the games. "
            text += "Let's talk about something else. "
            skill_state_update = {"next_step": ""}
            scenario = False
    elif "NO_ANSWER" in true_cmds:
        text = "You can always talk to me about other popular games. What do you want to talk about?"
        skill_state_update = {"next_step": ""}
        scenario = False
    else:
        top_index -= 1
        if top_index >= 0:
            current_game = top[top_index]
        else:
            current_game = {}
        text = "I didn't get what you've just said. "
        text += f"I talked about {current_game.get('name_original', 'games')}, do you want to continue. "
        text += "For example, you can say:  go on "
        text += "Or do you want to stop for now? "
        skill_state_update = {"next_step": "describe_top"}

    return state, text, confidence, skill_state_update, scenario


def select_top_handler(state, skill_state, true_model_names, true_cmds):
    confidence = 1.0
    scenario = True
    undefined_request = False

    if "last_year" in true_model_names:
        current_top = tops.get("previous_yearly_top", [])
        period_plh = "the last year"
        top_name = "previous_yearly_top"
    elif "this_year" in true_model_names:
        current_top = tops.get("yearly_top", [])
        period_plh = "this year"
        top_name = "yearly_top"
    elif "month" in true_model_names:
        current_top = tops.get("monthly_top", [])
        period_plh = "the last month"
        top_name = "monthly_top"
    elif "week" in true_model_names:
        current_top = tops.get("weekly_top", [])
        period_plh = "the last week"
        top_name = "weekly_top"
    else:
        undefined_request = True

    if "NO_ANSWER" in true_cmds:
        text = "You can always talk to me about other popular games. What do you want to talk about?"
        skill_state_update = {"next_step": ""}
        scenario = False
    elif undefined_request:
        text = "I didn't get what you've just said. "
        text += "Do you want to talk about the best games of the past year, this year, last month or week? "
        text += "For example, you can say: show me the best games of this year. "
        text += "Or do you want to stop for now? "
        skill_state_update = {"next_step": "select_top"}
    else:
        is_plh = "was" if len(current_top) == 1 else "were"
        game_plh = "game" if len(current_top) == 1 else "games"
        text = f" There {is_plh} {len(current_top)} newly released "
        text += f"{game_plh} highly rated in {period_plh}. Do you want to learn more? "
        skill_state_update = {"next_step": "describe_top", "top": current_top, "top_name": top_name, "top_index": 0}

    return state, text, confidence, skill_state_update, scenario


def intro_handler(state, skill_state, true_model_names, true_cmds):
    confidence = 1.0
    scenario = True
    if skill_state.get("top_name") == "previous_yearly_top":
        text = "Last time we talked about the best games of last year. "
    elif skill_state.get("top_name") == "yearly_top":
        text = "Last time we talked about the best games of this year. "
    elif skill_state.get("top_name") == "monthly_top":
        text = "Last time we talked about the best games of the last month. "
    elif skill_state.get("top_name") == "weekly_top":
        text = "Last time we talked about the best games of the last week. "
    else:
        text = "I can tell you about popular games. "

    text += "For now, I can talk about the most popular games for this or last year "
    if tops.get("weekly_top"):
        text += ", last month, or even the last week (hotties!). "
    elif tops.get("monthly_top"):
        text += " or even the last month (hotties!). "
    text += "Which of these time periods is of interest for you?"
    skill_state_update = {"next_step": "select_top"}

    return state, text, confidence, skill_state_update, scenario


def run_skill(state: State, modes: List = [skill_attrs.modes.intro]):

    skill_state = state.get_skill_state(skill_attrs.skill_name)
    model_results = run_models(models, state.human_utterances)
    true_model_names = cmd_postprocessing(model_results, model_name_only=True)
    true_cmds = cmd_postprocessing(model_results, cmd_only=True)
    text = "Sorry, i can not answer."
    confidence = 0.0
    scenario = False
    skill_state_update = {}

    print(f"<{skill_attrs.skill_name}> true_model_names: {true_model_names}")
    print(f"<{skill_attrs.skill_name}> true_cmds: {true_cmds}")

    if skill_attrs.modes.intro in modes:
        if set(true_model_names) & set(["last_year", "this_year", "month", "week"]):
            state, text, confidence, skill_state_update, scenario = select_top_handler(
                state, skill_state, true_model_names, true_cmds
            )
        else:
            state, text, confidence, skill_state_update, scenario = intro_handler(
                state, skill_state, true_model_names, true_cmds
            )
    else:
        current_step = skill_state.get("next_step", "")

        if current_step == "describe_top":
            state, text, confidence, skill_state_update, scenario = describe_top_handler(
                state, skill_state, true_model_names, true_cmds
            )
            state.update_st2_policy({"game_conversation": True})

        elif current_step == "select_top" or (set(true_model_names) & set(["last_year", "this_year", "month", "week"])):
            state, text, confidence, skill_state_update, scenario = select_top_handler(
                state, skill_state, true_model_names, true_cmds
            )

    state.add_hypothesis(
        skill_name=skill_attrs.skill_name, text=text, confidence=confidence, scenario=scenario,
    )
    state.update_skill_state(skill_attrs.skill_name, skill_state_update)

    return state