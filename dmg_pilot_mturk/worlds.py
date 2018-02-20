# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

# Code by Janosch Haber, University of Amsterdam. 2018

from parlai.mturk.core.worlds import MTurkTaskWorld
from parlai.core.worlds import validate
from joblib import Parallel, delayed
from parlai.tasks.dmg_pilot_mturk.agents import DMGMultiRoundTeacher
from parlai.tasks.dmg_pilot_mturk.agents import WELCOME_MESSAGE
from parlai.tasks.dmg_pilot_mturk.agents import SELECTION_TOKEN
from parlai.tasks.dmg_pilot_mturk.agents import COM_TOKEN
from parlai.tasks.dmg_pilot_mturk.agents import DIF_TOKEN
from parlai.tasks.dmg_pilot_mturk.agents import NEXT_ROUND_TOKEN
from parlai.tasks.dmg_pilot_mturk.agents import FEEDBACK_TOKEN

from collections import defaultdict
import random
import time


class MTurkDMGDialogWorld(MTurkTaskWorld):

    def __init__(self, opt, agents=None, shared=None):
        if agents is not None:
            random.shuffle(agents)
        self.agents = agents
        self.acts = [None] * len(agents)
        self.task = DMGMultiRoundTeacher(opt=opt)
        self.game_nr = 0
        self.round_nr = -1
        self.turn_nr = -1
        self.players = [agents[0].id, agents[1].id]
        self.player_labels = ["A", "B"]
        self.selections = defaultdict(lambda: dict())
        self.data = None
        self.common = None
        self.episodeDone = False
        self.doneCounter = 0

        self.conversation_log = {
            'game_id': self.game_nr,
            'players': self.players,
            'agent_ids': self.player_labels,
            # TODO: Add the actual agent ids
            'data': []
        }
        self.round_log = {
            'score': None,
            'images': None,
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
            self.common = list(set(self.data[self.player_labels[0]][self.round_nr])
                               .intersection(self.data[self.player_labels[1]][self.round_nr]))

            # Send a welcome message with the game data to all players
            for agent, player, player_label in zip(self.agents, self.players, self.player_labels):

                image_list = ""
                for image in self.data[player_label][self.round_nr]:
                    image_list += "{} \n".format(image)

                action = {}
                action['text'] = WELCOME_MESSAGE.format(self.round_nr+1, player, image_list)
                action['images'] = self.data[player_label][self.round_nr]
                print(action['images'])

                agent.observe(validate(action))

            self.turn_nr += 1

        # Else observe the actions of the players
        else:
            for agent, player, player_label in zip(self.agents, self.players, self.player_labels):

                # Obtain the action of a MTurk agent
                try:
                    action = agent.act(timeout=None)
                # Obtain the action of a local agent
                except TypeError:
                    action = agent.act()

                # Let the other agents observe the action
                for other_agent in self.agents:
                    if other_agent != agent:
                        other_agent.observe(validate(action))

                # Parse a selection
                message = action["text"]
                print("Message sent was: {}".format(message))

                log_entry = self.create_message_log_entry(agent, player, player_label, message)
                self.round_log['data'].append(log_entry)

                message = message.split(" ")
                if message[0] == SELECTION_TOKEN:
                    try:
                        assert len(message) == 3
                        image_id = message[-1]
                        image_type = message[1]
                        self.selections[agent][image_id] = image_type
                        print("Marked image {} as {}".format(image_id, image_type))

                    except:
                        print("WARNING: Your selection could not be parsed properly!")

                if message[0] == FEEDBACK_TOKEN and self.all_selected():
                    scores = self.send_feedback()
                    print("Logging data")
                    self.round_log['score'] = scores
                    self.round_log['images'] = {self.player_labels[0]: self.data[self.player_labels[0]][self.round_nr],
                                                self.player_labels[1]: self.data[self.player_labels[1]][self.round_nr]}
                    self.conversation_log['data'].append(self.round_log)

                if message[0] == NEXT_ROUND_TOKEN and self.all_selected() and self.doneCounter == 0:
                    print("One player clicked continue")
                    self.doneCounter += 1

                elif message[0] == NEXT_ROUND_TOKEN and self.all_selected() and self.doneCounter == 1:
                    print("Starting next round")
                    self.doneCounter = 0
                    self.episodeDone = True
                    self.selections = defaultdict(lambda: dict())

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

        scores = {self.players[0]: 0, self.players[1]: 0}

        # Send a feedback message to all players
        for agent, player in zip(self.agents, self.players):

            solutions = []

            feedback = "Feedback for Agent {}:\n".format(player)
            for image_id, selection in self.selections[agent].items():
                # file = "person_fridge_pilot/COCO_train2014_{:0>12d}.jpg".format(int(image_id))
                file = image_id
                feedback += "You marked image {} as ".format(image_id)
                if selection == COM_TOKEN: feedback += "common"
                elif selection == DIF_TOKEN: feedback += "different"
                feedback += " which was "
                if (selection == COM_TOKEN and file in self.common) \
                        or (selection == DIF_TOKEN and file not in self.common):
                    feedback += "correct.\n"
                    solutions.append([image_id, 1])
                    scores[player] += 1
                else:
                    feedback += "incorrect.\n"
                    solutions.append([image_id, 0])

            try:
                assert len(solutions) == 6
            except:
                print("Not all images marked yet!")
                continue

            action = {}
            action['text'] = feedback
            action['solution'] = solutions
            print(action['solution'])
            agent.observe(validate(action))

        print("Scores for this round are {}".format(scores))
        return scores

    def create_message_log_entry(self, agent, player, player_label, message):
        entry = {
            'timestamp': time.time(),
            'turn': self.turn_nr,
            'speaker:': player_label,
            'agent_id': player,
            # TODO: Add the actual player id
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
            if len(self.selections[agent]) < 6:
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
