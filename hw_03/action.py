import itertools


class Action:

    def __init__(self, name, parameters, positive_preconditions, negative_preconditions, add_effects, del_effects):
        self.name = name
        self.parameters = parameters
        self.positive_preconditions = [tuple(precondition) for precondition in positive_preconditions]
        self.negative_preconditions = [tuple(precondition) for precondition in negative_preconditions]
        self.add_effects = [tuple(effect) for effect in add_effects]
        self.del_effects = [tuple(effect) for effect in del_effects]
        self.weight = 1

    def __str__(self):
        return 'action: ' + self.name + \
               '\n  parameters: ' + str(self.parameters) + \
               '\n  positive_preconditions: ' + str(self.positive_preconditions) + \
               '\n  add_effects: ' + str(self.add_effects) + \
               '\n  del_effects: ' + str(self.del_effects) + '\n'

    def __hash__(self):
        return hash((tuple(self.parameters), self.name))

    def __eq__(self, other):
        return self.__dict__ == other.__dict__

    def groundify(self, objects):
        """ Generates all action's possible call combinations """
        if not self.parameters:
            yield self
            return
        type_map = []
        variables = []
        for var, var_type in self.parameters:
            type_map.append(objects[var_type])
            variables.append(var)
        for assignment in itertools.product(*type_map):
            if self.__skip_iteration(assignment):
                continue
            positive_preconditions = self.__replace(self.positive_preconditions, variables, assignment)
            negative_preconditions = self.__replace(self.negative_preconditions, variables, assignment)
            add_effects = self.__replace(self.add_effects, variables, assignment)
            del_effects = self.__replace(self.del_effects, variables, assignment)
            yield Action(self.name, assignment, positive_preconditions, negative_preconditions, add_effects,
                         del_effects)

    @staticmethod
    def __replace(group, variables, assignment):
        g = []
        for pred in group:
            pred = list(pred)
            iv = 0
            for v in variables:
                while v in pred:
                    pred[pred.index(v)] = assignment[iv]
                iv += 1
            g.append(pred)
        return g

    def __skip_iteration(self, assignment):
        if self.name == 'drive' or self.name == 'lift' or self.name == 'drop':
            if assignment[1] == assignment[2]:
                return True
            else:
                return False
        return False
