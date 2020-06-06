from pddl_parser import PddlParser
import copy

class Planner:
    def __init__(self, domain_file_name, problem_file_name):
        # Parser
        self.parser = PddlParser()
        self.parser.parse_domain(domain_file_name)
        self.parser.parse_problem(problem_file_name)
        self.action_state = {}  # An
        self.all_possible_actions = []
        self.generate_all_available_actions()
        self.states = {0: set(tuple(state + [0]) for state in self.parser.state)}
        self.g_node = 0

    def generate_all_available_actions(self):
        for action in self.parser.actions:
            for possible_act in action.groundify(self.parser.objects):
                self.all_possible_actions.append(possible_act)

    @staticmethod
    def applicable(state, precondition):
        return any([set(precondition).issubset(set(item)) for item in state])

    def relaxation_plan(self):
        current_state = 0  # S0
        while True:
            temp_state = self.states[current_state].copy()
            possible_actions = set()
            for action in self.all_possible_actions:
                action_flag = True
                pre_cond = action.positive_preconditions
                for precondition in pre_cond:
                    if not self.applicable(self.states[current_state], precondition):
                        action_flag = False
                        break
                if action_flag:
                    for precondition in pre_cond:
                        # find the precondition in temp_state
                        state_from_temp_state = \
                            [item for item in temp_state if set(precondition).issubset(set(item))][0]
                        action.weight += state_from_temp_state[len(state_from_temp_state) - 1]
                    action.weight += 1

                    for effect in action.add_effects:
                        # check effect exists already in state
                        if any([set(effect).issubset(set(item)) for item in temp_state]):
                            state_from_temp_state = [item for item in temp_state if set(effect).issubset(set(item))][0]
                            if state_from_temp_state[len(state_from_temp_state) - 1] > action.weight:
                                temp_state.remove(state_from_temp_state)
                                temp_state.add(state_from_temp_state[:len(state_from_temp_state) - 1] +
                                               (action.weight,))
                        else:
                            temp_state.add(effect + (action.weight,))
                    possible_actions.add(copy.deepcopy(action))

            if temp_state == self.states[current_state] or len(possible_actions) == 0:
                break
            else:
                self.action_state[current_state] = possible_actions
                current_state += 1
                self.states[current_state] = temp_state
                self.calculate_g_node(current_state)

        if self.g_node == 0:
            print("I could not succeed all goals")
        self.write_actions_states_occurred(current_state)

    def calculate_g_node(self, current_state):
        succeeded_goals = ([item for goal in self.parser.positive_goals for item in self.states[current_state] if
                            set(goal).issubset(set(item))])
        if len(self.parser.positive_goals) == len(succeeded_goals) and self.g_node == 0:
            for _succeeded_goal in succeeded_goals:
                self.g_node += _succeeded_goal[len(_succeeded_goal) - 1]

    def write_actions_states_occurred(self, current_state):
        data = 'Actions and States occurred per level \n' + '-' * 50 + '\n'
        for level in range(current_state):
            data += 'At level {} we had {} states and we found {} new actions\n'.format(
                level, len(self.states[level]), len(self.action_state[level]))
            data += '\nStates: \n'
            for state in self.states[level]:
                data += "%s - Hadd value: %d \n" % (', '.join(state[:len(state) - 1]), state[len(state) - 1])
            data += '\nActions: \n'
            for action in self.action_state[level]:
                data += action.__str__()
            data += '-' * 100 + '\n'

        # write last level's states
        data += 'At level {} we had {} states\n'.format(current_state, len(self.states[current_state]))
        data += '\nStates: \n'
        for state in self.states[current_state]:
            data += "%s - Hadd value: %d \n" % (', '.join(state[:len(state) - 1]), state[len(state) - 1])

        data += '\n' + '-' * 100 + '\n'
        if self.g_node == 0:
            data += "We did not find all goals so we did not calculate G node value"
        else:
            data += "G node had Hadd value = {}".format(self.g_node)

        with open('results.txt', 'w') as f:
            f.write(data)


if __name__ == '__main__':
    domain = "Depots.pddl"
    problem = "pfile1.pddl"
    planner = Planner(domain, problem)
    planner.relaxation_plan()
