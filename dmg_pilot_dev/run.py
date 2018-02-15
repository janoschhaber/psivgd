# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

# Code by Janosch Haber, University of Amsterdam. 2018

from parlai.core.params import ParlaiParser
from parlai.mturk.tasks.dmg_pilot_dev.worlds import LocalDMGDialogWorld
from parlai.agents.local_human.local_human import LocalHumanAgent
from task_config import task_config

from collections import defaultdict
import json


def main():
    """
    Main function for the DMG pilot data collection task
    :return: Nothing.
    """
    argparser = ParlaiParser(False, False)
    argparser.add_parlai_data_path()

    opt = argparser.parse_args()
    opt['task'] = 'dmg_pilot_dev'
    opt['datatype'] = 'dmg_pilot_data_1'
    opt.update(task_config)

    local_agent_1 = LocalHumanAgent(opt=None)
    local_agent_1.id = 'A'
    local_agent_2 = LocalHumanAgent(opt=None)
    local_agent_2.id = 'B'

    agents = [local_agent_1, local_agent_2]

    world = LocalDMGDialogWorld(
        opt=opt,
        agents=agents
    )

    # Loop over all five rounds of the game
    for r in range(5):
        print("--- Starting round {} ---".format(r+1))
        while not world.episode_done():
            world.parley()

        # Write the log data to file
        with open('logs/dmg_pilot_data_{}.json'.format(world.game_nr), 'w') as f:
            json.dump(world.conversation_log, f)

        # Reset the world for the next round
        world.round_log['data'] = []
        world.round_log['score'] = None
        world.selections = defaultdict(lambda: dict())
        world.turn_nr = -1
        world.round_nr += 1
        world.episodeDone = False

    world.shutdown()


if __name__ == '__main__':
    main()
