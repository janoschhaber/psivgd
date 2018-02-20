# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

# Code by Janosch Haber, University of Amsterdam. 2018

from parlai.core.params import ParlaiParser
from parlai.mturk.core.mturk_manager import MTurkManager
from parlai.mturk.tasks.dmg_pilot_mturk.worlds import MTurkDMGDialogWorld
from parlai.agents.local_human.local_human import LocalHumanAgent
from parlai.core.agents import create_agent
from task_config import task_config

from collections import defaultdict
import json
import os
import time


def main():
    """
    Main function for the DMG pilot data collection task
    :return: Nothing.
    """
    argparser = ParlaiParser(False, False)
    argparser.add_parlai_data_path()
    argparser.add_mturk_args()
    argparser.add_argument('--two_mturk_agents', dest='two_mturk_agents',
                           action='store_true', help='data collection mode '
                           'with converations between two MTurk agents')

    opt = argparser.parse_args()
    opt['task'] = 'dmg_pilot_dev'
    opt['datatype'] = 'dmg_pilot_data_1'
    opt.update(task_config)

    local_agent_1_id = 'local_1'
    mturk_agent_ids = ['mturk_agent_1']
    if opt['two_mturk_agents']:
        mturk_agent_ids.append('mturk_agent_2')

    mturk_manager = MTurkManager(
        opt=opt,
        mturk_agent_ids=mturk_agent_ids
    )

    mturk_manager.setup_server()

    try:
        mturk_manager.start_new_run()
        mturk_manager.create_hits()

        mturk_manager.set_onboard_function(onboard_function=None)
        mturk_manager.ready_to_accept_workers()

        def check_worker_eligibility(worker):
            return True

        def assign_worker_roles(workers):
            for index, worker in enumerate(workers):
                worker.id = mturk_agent_ids[index % len(mturk_agent_ids)]

        def run_conversation(mturk_manager, opt, workers):
            agents = workers[:]

            # Create a local agent
            if not opt['two_mturk_agents']:
                if 'model' in opt:
                    local_agent = create_agent(opt)
                else:
                    local_agent = LocalHumanAgent(opt=None)

                local_agent.id = local_agent_1_id
                agents.append(local_agent)

            opt["batchindex"] = mturk_manager.started_conversations

            world = MTurkDMGDialogWorld(
                opt=opt,
                agents=agents
            )

            # Loop over all five rounds of the game
            for r in range(5):
                print("--- Starting round {} ---".format(r+1))
                while not world.episode_done():
                    world.parley()

                # TODO: Enable logging
                # Write the log data to file

                print("Writing log to file")
                if not os.path.exists("logs"):
                    os.makedirs("logs")
                with open('logs/dmg_pilot_data_{}_{}.json'.format(world.game_nr, time.time()), 'w') as f:
                    json.dump(world.conversation_log, f)

                if not r == 4:
                    # Reset the world for the next round
                    world.round_log['data'] = []
                    world.round_log['score'] = None
                    world.selections = defaultdict(lambda: dict())
                    world.turn_nr = -1
                    world.round_nr += 1
                    world.episodeDone = False

                else:
                    world.shutdown()

        mturk_manager.start_task(
            eligibility_function=check_worker_eligibility,
            assign_role_function=assign_worker_roles,
            task_function=run_conversation
        )

    except BaseException:
        raise
    finally:
        mturk_manager.expire_all_unassigned_hits()
        mturk_manager.shutdown()

if __name__ == '__main__':
    main()
