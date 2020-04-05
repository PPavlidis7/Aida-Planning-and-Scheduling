from pddl_parser import PddlParser


class Planner:
    def __init__(self, domain_file_name, problem_file_name):
        # Parser
        self.parser = PddlParser()
        self.parser.parse_domain(domain_file_name)
        self.parser.parse_problem(problem_file_name)
        self.action_state = {}  # An
        self.all_possible_actions = []
        self.generate_all_available_actions()
        self.states = {0: set(tuple(state) for state in self.parser.state)}

    def generate_all_available_actions(self):
        for action in self.parser.actions:
            for possible_act in action.groundify(self.parser.objects):
                self.all_possible_actions.append(possible_act)

    @staticmethod
    def applicable(state, precondition):
        return tuple(precondition) in state

    def graph_plan(self):
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
                    for effect in action.add_effects:
                        temp_state.add(effect)
                    possible_actions.add(action)

            if temp_state == self.states[current_state] or len(possible_actions) == 0:
                break
            else:
                self.action_state[current_state] = possible_actions
                current_state += 1
                self.states[current_state] = temp_state

        self.write_actions_states_occurred(current_state)

    def write_actions_states_occurred(self, current_state):
        data = 'Actions and States occurred per level \n' + '-'*50 + '\n'
        for level in range(current_state):
            data += 'At level {} we had {} states and we found {} new actions\n'.format(
                level, len(self.states[level]), len(self.action_state[level]))
            data += '\nStates: \n'
            for state in self.states[level]:
                data += "%s \n" % ', '.join(state)
            data += '\nActions: \n'
            for action in self.action_state[level]:
                data += action.__str__()
            data += '-'*100 + '\n'

        # write last level's states
        data += 'At level {} we had {} states\n'.format(current_state, len(self.states[current_state]))
        data += '\nStates: \n'
        for state in self.states[current_state]:
            data += "%s \n" % ', '.join(state)

        with open('graphPlan_states_actions.txt', 'w') as f:
            f.write(data)


if __name__ == '__main__':
    domain = "Depots.pddl"
    problem = "pfile1.pddl"
    planner = Planner(domain, problem)
    planner.graph_plan()
