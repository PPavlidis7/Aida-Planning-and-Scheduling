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
        self.possible_states = self.generate_all_possible_state_values()
        self.states = {0: set(tuple(state) for state in self.parser.state)}
        self.write_available_grounds()
        self.inconsistent_effects = {
            'all_mutexes': set(),  # all mutexes that we found
            0: set()  # mutexes that we found in level 0
        }
        self.interference = {
            'all_mutexes': set(),  # all mutexes that we found
            0: set()  # mutexes that we found in level 0
        }
        self.inconsistent_support = {
            'all_mutexes': set(),  # all mutexes that we found
            0: set()  # mutexes that we found in level 0
        }

    def generate_all_available_actions(self):
        for action in self.parser.actions:
            for possible_act in action.groundify(self.parser.objects):
                self.all_possible_actions.append(possible_act)

    def generate_all_possible_state_values(self):
        __states = {}
        for state, state_parameters in self.parser.predicates.items():
            __states[state] = []
            if len(state_parameters) == 1:
                __states[state] = self.parser.objects[state_parameters[list(state_parameters.keys())[0]]]
            else:
                tmp_list_1 = self.parser.objects[state_parameters[list(state_parameters.keys())[0]]]
                tmp_list_2 = self.parser.objects[state_parameters[list(state_parameters.keys())[1]]]
                __states[state] = [(x, y) for x in tmp_list_1 for y in tmp_list_2 if x != y]
        return __states

    def write_available_grounds(self):
        # write ground facts
        data = 'Ground facts: \n' + '-' * 50 + '\n'
        for fact_type, facts in self.possible_states.items():
            for fact in facts:
                if type(fact) == list:
                    data += "%s %s \n" % (fact_type, ', '.join(fact))
                    data += "not %s %s \n" % (fact_type, ', '.join(fact))
                else:
                    data += "%s %s \n" % (fact_type, fact)
                    data += "not %s %s \n" % (fact_type, fact)
        with open('ground_facts_actions.txt', 'w') as f:
            f.write(data)

        # write ground actions
        data = 'Ground actions: \n' + '-' * 50 + '\n'
        for action in self.all_possible_actions:
            data += action.__str__()
        with open('ground_facts_actions.txt', 'a') as f:
            f.write(data)

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
                    for effect in action.del_effects:
                        temp_state.add(tuple(['not']) + effect)
                    for effect in action.add_effects:
                        temp_state.add(effect)
                    possible_actions.add(action)

            if temp_state == self.states[current_state] or len(possible_actions) == 0:
                break
            else:
                self.action_state[current_state] = possible_actions
                self.update_mutexes(current_state)
                current_state += 1
                self.states[current_state] = temp_state

        self.write_actions_states_occurred(current_state)
        self.write_mutexes()

    def update_mutexes(self, last_state_level):
        concated_actions = set()
        for level, actions in self.action_state.items():
            for action in actions:
                concated_actions.add(action)

        # inconsistent effects
        self.inconsistent_effects[last_state_level] = set()
        for action_1 in concated_actions:
            for action_2 in concated_actions:
                if action_1 != action_2 and len(set(action_1.del_effects).intersection(action_2.add_effects)):
                    if (action_1, action_2,) not in self.inconsistent_effects['all_mutexes'] and \
                            (action_2, action_1) not in self.inconsistent_effects['all_mutexes']:
                        self.inconsistent_effects['all_mutexes'].add((action_1, action_2))
                        self.inconsistent_effects[last_state_level].add((action_1, action_2))

            for state in self.states[last_state_level]:
                if state in action_1.del_effects and (action_1, state,) not in self.inconsistent_effects['all_mutexes']:
                    self.inconsistent_effects['all_mutexes'].add((action_1, state))
                    self.inconsistent_effects[last_state_level].add((action_1, state))

        # interference
        self.interference[last_state_level] = set()
        for action_1 in concated_actions:
            for action_2 in concated_actions:
                if action_1 != action_2 and len(
                        set(action_1.del_effects).intersection(action_2.positive_preconditions)):
                    if (action_1, action_2,) not in self.interference['all_mutexes'] and \
                            (action_2, action_1) not in self.interference['all_mutexes']:
                        self.interference['all_mutexes'].add((action_1, action_2))
                        self.interference[last_state_level].add((action_1, action_2))

        # inconsistent support
        self.inconsistent_support[last_state_level] = set()
        for state_1 in self.states[last_state_level]:
            for state_2 in self.states[last_state_level]:
                if (('not',) + state_1 == state_2 or state_1 == state_2 + ('not',)) and \
                        ((state_1, state_2) not in self.inconsistent_support['all_mutexes'] and
                         (state_2, state_1) not in self.inconsistent_support['all_mutexes']):
                    self.inconsistent_support['all_mutexes'].add((state_1, state_2))
                    self.inconsistent_support[last_state_level].add((state_1, state_2))

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

    def write_mutexes(self):
        data = 'Mutexes found: \n'
        data += 'Inconsistent effects:\n'
        for level, mutexes in self.inconsistent_effects.items():
            if level == 'all_mutexes':
                continue
            data += 'At level {}:\n'.format(level)
            if not len(mutexes):
                data += 'No mutexes\n' + '-' * 100 + '\n'
            else:
                for mutex_pair in mutexes:
                    data += mutex_pair[0].__str__()
                    data += mutex_pair[1].__str__()
                    data += '\n' + '-' * 100 + '\n'

        data += '\n{}\nInterference:\n'.format('-'*100)
        for level, mutexes in self.interference.items():
            if level == 'all_mutexes':
                continue
            data += 'At level {}:\n'.format(level)
            if not len(mutexes):
                data += 'No mutexes\n' + '-' * 100 + '\n'
            else:
                for mutex_pair in mutexes:
                    data += mutex_pair[0].__str__()
                    data += mutex_pair[1].__str__()
                    data += '\n' + '-' * 100 + '\n'

        data += '\n{}\nInconsistent support:\n'.format('-' * 100)
        for level, mutexes in self.inconsistent_support.items():
            if level == 'all_mutexes':
                continue
            data += 'At level {}:\n'.format(level)
            if not len(mutexes):
                data += 'No mutexes\n' + '-' * 100 + '\n'
            else:
                for mutex_pair in mutexes:
                    data += mutex_pair[0].__str__() + '\t\t'
                    data += mutex_pair[1].__str__()
                    data += '\n' + '-' * 100 + '\n'

        with open('graphPlan_mutexes.txt', 'w') as f:
            f.write(data)


if __name__ == '__main__':
    domain = "Depots.pddl"
    problem = "pfile1.pddl"
    planner = Planner(domain, problem)
    planner.graph_plan()
