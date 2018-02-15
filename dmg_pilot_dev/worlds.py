# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

# Code by Janosch Haber, University of Amsterdam. 2018

from parlai.core.worlds import MultiAgentDialogWorld
from parlai.core.worlds import validate
from joblib import Parallel, delayed
from parlai.tasks.dmg_pilot_dev.agents import DMGMultiRoundTeacher
from parlai.tasks.dmg_pilot_dev.agents import WELCOME_MESSAGE
from parlai.tasks.dmg_pilot_dev.agents import SELECTION_TOKEN
from parlai.tasks.dmg_pilot_dev.agents import COM_TOKEN
from parlai.tasks.dmg_pilot_dev.agents import DIF_TOKEN

from collections import defaultdict
import random
import time


class LocalDMGDialogWorld(MultiAgentDialogWorld):

    def __init__(self, opt, agents=None, shared=None):
        if agents is not None:
            random.shuffle(agents)
        self.agents = agents
        self.acts = [None] * len(agents)
        self.task = DMGMultiRoundTeacher(opt=opt)
        self.game_nr = 0
        self.round_nr = -1
        self.turn_nr = -1
        self.players = ['A', 'B']
        self.selections = defaultdict(lambda: dict())
        self.data = None
        self.common = None
        self.episodeDone = False

        self.conversation_log = {
            'game_id': self.game_nr,
            # 'agents': self.agents,
            'players': self.players,
            'data': []
        }
        self.round_log = {
            'score': None,
            'data': []
        }

    def parley(self):
        """
        Main communication loop for the agents involved in the task
        :return: Nothing
        """

        # If a new round has started, load the game data (if necessary) and send it to the players
        if self.turn_nr == -1:
            # Load a new game (data) if no game is running yet
            if self.round_nr == -1 and not self.data:
                self.data = self.task.episodes[self.game_nr % len(self.task.episodes)]
                self.round_nr = 0

            # Determine the common images
            self.common = list(set(self.data[self.players[0]][self.round_nr])
                               .intersection(self.data[self.players[1]][self.round_nr]))

            # Send a welcome message with the game data to all players
            for agent, player in zip(self.agents, self.players):

                image_list = ""
                for image in self.data[player][self.round_nr]:
                    image_list += "{} \n".format(image)

                action = {}
                action['text'] = WELCOME_MESSAGE.format(self.round_nr+1, player, image_list)
                action['images'] = self.data[player][self.round_nr]

                agent.observe(validate(action))

            self.turn_nr += 1

        # Else observe the actions of the players
        else:
            for agent, player in zip(self.agents, self.players):

                # Obtain the action of a MTurk agent
                try:
                    action = agent.act(timeout=None)
                # Obtain the action of a local agent
                except TypeError:
                    action = agent.act()

                # Observe the other agents
                for other_agent in self.agents:
                    if other_agent != agent:
                        other_agent.observe(validate(action))

                # Parse a selection
                message = action["text"]

                log_entry = self.create_message_log_entry(agent, player, message)
                self.round_log['data'].append(log_entry)

                message = message.split(" ")
                # TODO: Set turn number requirement to 1 in order to prevent selections before the first message
                if message[0] == SELECTION_TOKEN and self.turn_nr > 0:
                    try:
                        assert len(message) == 3
                        image_id = message[-1]
                        image_type = message[1]
                        self.selections[agent][image_id] = image_type
                        # print("Added image {} to the {} list of agent {} who is player {}"
                        #       .format(image_id, image_type, agent, player))

                    except:
                        print("WARNING: Your selection could not be parsed properly!")

                    if self.all_selected():
                        self.episodeDone = True

                        scores = self.send_feedback()
                        self.round_log['score'] = scores
                        self.conversation_log['data'].append(self.round_log)

                # Check if episode ended due to disconnection or timeout or returned hit
                elif action['episode_done']:
                    self.episodeDone = True

            self.turn_nr += 1

    def send_feedback(self):
        """
        Sends feedback to the player after each round of the game and calculates the scores
        :return: The scores for all players. 6 points means all images marked correctly, 0 points means zero correct.
        """
        # print("The common images were {}".format(self.common))

        scores = {'A': 0, 'B': 0}

        # Send a feedback message to all players
        for agent, player in zip(self.agents, self.players):

            feedback = "Feedback for Agent {}:\n".format(player)
            for image_id, selection in self.selections[agent].items():
                file = "person_fridge_pilot/COCO_train2014_{:0>12d}.jpg".format(int(image_id))
                feedback += "You marked image {} as ".format(image_id)
                if selection == COM_TOKEN: feedback += "common"
                elif selection == DIF_TOKEN: feedback += "different"
                feedback += " which was "
                if (selection == COM_TOKEN and file in self.common) \
                        or (selection == DIF_TOKEN and file not in self.common):
                    feedback += "correct.\n"
                    scores[player] += 1
                else:
                    feedback += "incorrect.\n"

            action = {}
            action['text'] = feedback
            agent.observe(validate(action))

        print("Scores for this round are {}".format(scores))
        return scores

    def create_message_log_entry(self, agent, player, message):
        entry = {
            'timestamp': time.time(),
            'turn': self.turn_nr,
            'speaker:': player,
            # 'agent_id': agent,
            'message': message
        }
        return entry

    def all_selected(self):
        """
        Returns True if all players selected all images
        :return: True if all players selected all images
        """
        for agent in self.agents:
            # TODO: Set image number requirement to 6 to account for all images
            if len(self.selections[agent]) < 1:
                return False
        return True

    def episode_done(self):
        """
        Returns True if the current game round (episode) is done
        :return: True if the current game round (episode) is done
        """
        return self.episodeDone

    def shutdown(self):
        """
        Shuts down all mturk agents in parallel
        (if one mturk agent is disconnected then it could prevent other mturk agents from completing.)
        """
        global shutdown_agent

        def shutdown_agent(agent):
            # Shut down MTurk agents
            try:
                agent.shutdown(timeout=None)
            # Shut down local agents
            except Exception:
                agent.shutdown()

        Parallel(n_jobs=len(self.agents), backend='threading')\
            (delayed(shutdown_agent)(agent) for agent in self.agents)
