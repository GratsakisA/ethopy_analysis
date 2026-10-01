# task id (43) (free water A, B and detection)  --- ruff applied

# This task conists of two difficulty levels:
# difficulty -10: free water A (120μl) with 0ms init_ready | rew_prob: -1
# difficulty -9: free water B (120μl) with 50ms init_ready | rew_prob: -1
# difficulty -8: detection task with 50ms init_ready | rew_prob: 1,2
import time

import numpy as np
from scipy import interpolate

from ethopy.behaviors.multi_port import MultiPort
from ethopy.experiments.match_port import Experiment
from ethopy.stimuli.panda import Panda

interp = (
    lambda x: interpolate.splev(
        np.linspace(0, len(x), 100),
        interpolate.splrep(np.linspace(0, len(x), len(x)), x),
    )
    if len(x) > 3
    else x
)

# define session parameters
session_params = {
    "setup_conf_idx": 7,
    "max_reward": 2000,
    "min_reward": 700,
    "hydrate_delay": 30,
}

exp = Experiment()
exp.setup(logger, MultiPort, session_params)


# ---------------------------------------------------------------------
exp.interface.give_liquid(1, 100)  # keep valve 1 open for 100ms
time.sleep(2)  # Pause to ensure valve closes
exp.interface.give_liquid(2, 100)  # keep valve 2 open for 100ms
time.sleep(1)
# ---------------------------------------------------------------------

conditions = []

panda_obj = Panda()
panda_obj.fill_colors.set(
    {
        "background": (0, 0, 0),
        "start": (0.2, 0.2, 0.2),
        "reward": (0.6, 0.6, 0.6),
        "punish": (0, 0, 0),
    }
)

resp_obj = [1, 2]
x_pos = [-0.3, 0.3]
reward_amount = 6

# rotation of the object
rot_f = lambda: interp((np.random.rand(20) - 0.5) * 100)
rots = rot_f()


# Free Water A (120μl) --------

# define environment conditions
free_water_A = {
    "init_ready": 0,
    "trial_duration": 10000,
    "abort_duration": 500,
    "punish_duration": 10000,
    "reward_duration": 5000,
    "intertrial_duration": 500,
}

block_A = exp.Block(
    difficulty=-10,
    next_up=-9,
    next_down=-10,
    staircase_window=30,
    trial_selection="staircase",
    antibias=True,
)

for idx, obj_id in enumerate(resp_obj):
    conditions += exp.make_conditions(
        stim_class=panda_obj,
        conditions={
            **free_water_A,
            **block_A.dict(),
            "obj_id": resp_obj[idx],
            "obj_dur": 10000,
            "obj_pos_x": x_pos[idx],
            "obj_pos_y": 0.02,
            "obj_mag": 0,  
            "obj_rot": (rots, rots),  
            "obj_tilt": (0, 0),  
            "reward_port": -1,
            "response_port": -1,
            "reward_amount": reward_amount,
        },
    )

# Free Water B (180μl) --------
free_water_B = {
    "init_ready": 50,
    "trial_duration": 9000,
    "abort_duration": 500,
    "punish_duration": 10000,
    "reward_duration": 5000,
    "intertrial_duration": 500,
}

block_B = exp.Block(
    difficulty=-9,
    next_up=-8,
    next_down=-9,
    staircase_window=30,
    trial_selection="staircase",
    antibias=True,
)

for idx, obj_id in enumerate(resp_obj):
    conditions += exp.make_conditions(
        stim_class=panda_obj,
        conditions={
            **free_water_B,
            **block_B.dict(),
            "obj_id": resp_obj[idx],
            "obj_dur": 10000,
            "obj_pos_x": x_pos[idx],
            "obj_pos_y": 0.02,
            "obj_mag": 0, 
            "obj_rot": (rots, rots), 
            "obj_tilt": (0, 0), 
            "reward_port": -1,
            "response_port": -1,
            "reward_amount": reward_amount,
        },
    )

# Detection --------

rew_prob = [1,2] 

block_detect = exp.Block(
    difficulty=-8,
    next_up=-8,
    next_down=-8,
    staircase_window=30,
    trial_selection="staircase",
    antibias=True,
)

for idx, obj_id in enumerate(resp_obj):
    conditions += exp.make_conditions(
        stim_class=panda_obj,
        conditions={
            **free_water_B,
            **block_detect.dict(),
            "obj_id": resp_obj[idx],
            "obj_dur": 10000,
            "obj_pos_x": x_pos[idx],
            "obj_pos_y": 0.02,
            "obj_mag": 0.5, 
            "obj_rot": (rots, rots), 
            "obj_tilt": (0, 0),  
            "reward_port": [rew_prob[idx]],
            "response_port": [rew_prob[idx]],
            "reward_amount": reward_amount,
        },
    )


# run experiments
exp.push_conditions(conditions)
exp.start()

