import re

from action import Action


class PddlParser:
    SUPPORTED_REQUIREMENTS = [':strips', ':typing']

    def __init__(self):
        self.predicates = {}
        self.actions = []
        self.negative_goals = []
        self.positive_goals = []
        self.objects = {}
        self.state = []
        self.domain_name = 'unknown'
        self.problem_name = 'unknown'
        self.requirements = []
        self.types = {}

    @staticmethod
    def __scan_tokens(filename):
        with open(filename, 'r') as f:
            # Remove single line comments
            __data = re.sub(r';.*$', '', f.read(), flags=re.MULTILINE).lower()
        # Tokenize
        stack = []
        __temp_list = []
        for __character in re.findall(r'[()]|[^\s()]+', __data):
            if __character == '(':
                stack.append(__temp_list)
                __temp_list = []
            elif __character == ')':
                if stack:
                    __temp_list_2 = __temp_list
                    __temp_list = stack.pop()
                    __temp_list.append(__temp_list_2)
                else:
                    raise Exception('Missing open parentheses')
            else:
                __temp_list.append(__character)
        if stack:
            raise Exception('Missing close parentheses')
        if len(__temp_list) != 1:
            raise Exception('Malformed expression')
        return __temp_list[0]

    def parse_domain(self, domain_filename):
        tokens = self.__scan_tokens(domain_filename)
        if type(tokens) is list and tokens.pop(0) == 'define':
            while tokens:
                group = tokens.pop(0)
                t = group.pop(0)
                if t == 'domain':
                    self.domain_name = group[0]
                elif t == ':requirements':
                    for req in group:
                        if req not in self.SUPPORTED_REQUIREMENTS:
                            raise Exception('Requirement ' + req + ' not supported')
                    self.requirements = group
                elif t == ':predicates':
                    self.__parse_predicates(group)
                elif t == ':types':
                    __tmp_list = []
                    __tmp_dict = {}
                    for index, value in enumerate(group):
                        if value != '-':
                            if value in __tmp_dict and group[index - 1] == '-':
                                continue
                            __tmp_list.append(value)
                            __tmp_dict[value] = []
                        else:
                            if group[index + 1] in __tmp_dict:
                                __tmp_dict[group[index + 1]] += __tmp_list
                            else:
                                __tmp_dict[group[index + 1]] = __tmp_list
                            __tmp_list = []
                    # __tmp_dict['locatable'] += __tmp_dict['surface']
                    self.types = __tmp_dict
                elif t == ':action':
                    self.__parse_action(group)
                else:
                    print(str(t) + ' is not recognized in domain')
        else:
            raise Exception('File ' + domain_filename + ' does not match domain pattern')

    def __parse_predicates(self, group):
        for pred in group:
            predicate_name = pred.pop(0)
            if predicate_name in self.predicates:
                raise Exception('Predicate ' + predicate_name + ' redefined')
            arguments = {}
            untyped_variables = []
            while pred:
                t = pred.pop(0)
                if t == '-':
                    if not untyped_variables:
                        raise Exception('Unexpected hyphen in predicates')
                    item_type = pred.pop(0)
                    while untyped_variables:
                        arguments[untyped_variables.pop(0)] = item_type
                else:
                    untyped_variables.append(t)
            while untyped_variables:
                arguments[untyped_variables.pop(0)] = 'object'
            self.predicates[predicate_name] = arguments

    def __parse_action(self, group):
        name = group.pop(0)
        if not type(name) is str:
            raise Exception('Action without name definition')
        for act in self.actions:
            if act.name == name:
                raise Exception('Action ' + name + ' redefined')
        parameters = []
        positive_preconditions = []
        negative_preconditions = []
        add_effects = []
        del_effects = []
        while group:
            t = group.pop(0)
            if t == ':parameters':
                if not type(group) is list:
                    raise Exception('Error with ' + name + ' parameters')
                parameters = []
                untyped_parameters = []
                p = group.pop(0)
                while p:
                    t = p.pop(0)
                    if t == '-':
                        if not untyped_parameters:
                            raise Exception('Unexpected hyphen in ' + name + ' parameters')
                        ptype = p.pop(0)
                        while untyped_parameters:
                            parameters.append([untyped_parameters.pop(0), ptype])
                    else:
                        untyped_parameters.append(t)
                while untyped_parameters:
                    parameters.append([untyped_parameters.pop(0), 'object'])
            elif t == ':precondition':
                self.__split_predicates(group.pop(0), positive_preconditions, negative_preconditions, name,
                                      ' preconditions')
            elif t == ':effect':
                self.__split_predicates(group.pop(0), add_effects, del_effects, name, ' effects')
            else:
                print(str(t) + ' is not recognized in action')
        self.actions.append(
            Action(name, parameters, positive_preconditions, negative_preconditions, add_effects, del_effects))

    def parse_problem(self, problem_filename):
        tokens = self.__scan_tokens(problem_filename)
        if type(tokens) is list and tokens.pop(0) == 'define':
            while tokens:
                group = tokens.pop(0)
                t = group[0]
                if t == 'problem':
                    self.problem_name = group[-1]
                elif t == ':domain':
                    if self.domain_name != group[-1]:
                        raise Exception('Different domain specified in problem file')
                elif t == ':requirements':
                    pass  # Ignore requirements in problem, parse them in the domain
                elif t == ':objects':
                    group.pop(0)
                    object_list = []
                    while group:
                        if group[0] == '-':
                            group.pop(0)
                            self.objects[group.pop(0)] = object_list
                            object_list = []
                        else:
                            object_list.append(group.pop(0))
                    if object_list:
                        if 'object' not in self.objects:
                            self.objects['object'] = []
                        self.objects['object'] += object_list
                    for type_name, type_subtypes in self.types.items():
                        if type_name == 'object':
                            continue
                        if type_name not in self.objects and type_subtypes != []:
                            self.objects[type_name] = []
                            for subtype in type_subtypes:
                                if type_name == 'locatable' and subtype == 'surface':
                                    for tmp_subtype in self.types[subtype]:
                                        self.objects[type_name] += self.objects[tmp_subtype]
                                else:
                                    self.objects[type_name] += self.objects[subtype]
                elif t == ':init':
                    group.pop(0)
                    self.state = group
                elif t == ':goal':
                    self.__split_predicates(group[1], self.positive_goals, self.negative_goals, '', 'goals')
                else:
                    print(str(t) + ' is not recognized in problem')
        else:
            raise Exception('File ' + problem_filename + ' does not match problem pattern')

    @staticmethod
    def __split_predicates(group, pos, neg, name, part):
        if not type(group) is list:
            raise Exception('Error with ' + name + part)
        if group[0] == 'and':
            group.pop(0)
        else:
            group = [group]
        for predicate in group:
            if predicate[0] == 'not':
                if len(predicate) != 2:
                    raise Exception('Unexpected not in ' + name + part)
                neg.append(predicate[-1])
            else:
                pos.append(predicate)
