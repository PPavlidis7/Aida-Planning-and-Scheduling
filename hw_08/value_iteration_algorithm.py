__author__ = "Pavlidis Pavlos"
"""
This script implements value iteration algorithm and it's based on:
https://automaticaddison.com/how-reinforcement-learning-works/?fbclid=IwAR2skABHP8FTsYibLhgyCm8PTHHjjFC8TRdFMhY9wqjwX8tRD0XQMyNXKT8
and
https://automaticaddison.com/value-iteration-vs-q-learning-algorithm-in-python-step-by-step/?fbclid=IwAR0XTB9V_tR9_hmK-7MJG8Z2o29-P3usdUi5bosKvu2VRdHWzSJdSMMrPdY
"""
import os
import time
from copy import deepcopy
from random import choice
from random import random

import numpy as np

# Constants
ALGORITHM_NAME = "Value_Iteration"
FILENAME = "race_env.txt"
START = 'S'
GOAL = 'F'
WALL = '#'
TRACK = '.'
MAX_VELOCITY = 2
MIN_VELOCITY = -2
DISC_RATE = 0.9  # Discount rate, also known as gamma. Determines by how much we discount the value of a future state s'
ERROR_THRESHOLD = 0.001  # Determine when Q-values stabilize (i.e.theta)
PROB_ACCELER_FAILURE = 0.20  # Probability car will try to take action a according to policy pi(s) = a and fail.
PROB_ACCELER_SUCCESS = 1 - PROB_ACCELER_FAILURE
NO_TRAINING_ITERATIONS = 40  # A single training iteration runs through all possible states s
NO_RACES = 5  # How many times the race car does a single time trial from starting position to the finish line
FRAME_TIME = 0.7  # How many seconds between frames printed to the console
MAX_STEPS = 1000  # Maximum number of steps the car can take during time trial
HIT_WALL_PENALTY = -10.0    # Cost if car hits wall
STEP_COST = -1.0
VELOCITY_RANGE = range(MIN_VELOCITY, MAX_VELOCITY + 1)  # Race car velocity range in both y and x directions
REWARD = 100.0  # Reward for finish line
# All actions that the race car can take (acceleration in x direction, acceleration in y direction)
ACTIONS = [
    (-2, -2), (-1, -2), (0, -2), (1, -2), (2, -2),
    (-2, -1), (-1, -1), (0, -1), (1, -1), (2, -1),
    (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0),
    (-2, 1), (-1, 1), (0, 1), (1, 1), (2, 1),
    (-2, 2), (-1, 2), (0, 2), (1, 2), (2, 2)
]


def read_environment(filename):
    """
    This method reads in the environment (i.e. racetrack)
    :param filename: str
    :return environment: list of lists
    :rtype list
    """
    with open(filename, 'r') as file:
        # Read until end of file using readline()
        # readline() then returns a list of the lines
        # of the input file
        # environment_data = file.readlines()
        environment = [[value for value in line.strip()] for line in file.readlines()]
    return environment


def print_environment(environment, car_position=(0, 0)):
    """
    This method reads in the environment and current (x,y) position of the car and prints the environment to the console
    :param list environment: The environment
    :param list car_position: The current car position
    """
    # Store value of current grid square
    temp = environment[car_position[0]][car_position[1]]
    # Move the car to current grid square
    environment[car_position[0]][car_position[1]] = "X"
    # Delay
    time.sleep(FRAME_TIME)
    # Clear the printed output
    os.system('cls')

    # For each line in the environment
    for line in environment:
        # Initialize a string
        text = ""
        # Add each character to create a line
        for character in line:
            text += character
        # Print the line of the environment
        print(text)
    # Restore value of current grid square
    environment[car_position[0]][car_position[1]] = temp


def get_random_start_position(environment):
    """
    This method reads in the environment and selects a random starting position on the racetrack (x, y) from the
    available starting positions. Note that (0,0) corresponds to the upper left corner of the racetrack.
    :param list environment: list of lines
    :return random starting coordinate (x,y) on the racetrack
    :rtype tuple
    """
    # Collect all possible starting positions on the racetrack
    starting_positions = []
    for x, row in enumerate(environment):
        for y, col in enumerate(row):
            # If we are at the starting position
            if col == START:
                # Add the coordinate to the list of available starting positions in the environment
                starting_positions += [(x, y)]
    # Select a starting position
    start_position = choice(starting_positions)
    return start_position


def get_new_velocity(old_vel, accel, min_vel=MIN_VELOCITY, max_vel=MAX_VELOCITY):
    """
    Get the new velocity values
    :param tuple old_vel: (vx, vy)
    :param tuple accel: (ax, ay)
    :param int min_vel: Minimum velocity of the car
    :param int max_vel: Maximum velocity of the car
    :return new velocities in x and y directions
    """
    new_y = old_vel[0] + accel[0]
    new_x = old_vel[1] + accel[1]
    if new_x < min_vel:
        new_x = min_vel
    if new_x > max_vel:
        new_x = max_vel
    if new_y < min_vel:
        new_y = min_vel
    if new_y > max_vel:
        new_y = max_vel

    return new_x, new_y


def get_nearest_open_cell(environment, x_crash, y_crash, vx=0, vy=0, acceptable_cells=(TRACK, START, GOAL)):
    """
    Locate the nearest open cell in order to handle crash scenario. Distance is calculated as the Manhattan distance.
    Start from the crash grid square and expand outward from there with a radius of 1, 2, 3, etc.
    Forms a diamond search pattern. For example, a Manhattan distance of 2 would look like the following:
            .
           ...
          ..#..
           ...
            .
    If velocity is provided, search in opposite direction of velocity so that
    there is no movement over walls
    :param list environment: The environment
    :param int x_crash: x coordinate where crash happened
    :param int y_crash: y coordinate where crash happened
    :param int vx: velocity in x direction when crash occurred
    :param int vy: velocity in y direction when crash occurred
    :param list of strings acceptable_cells: Contains environment types
    :return tuple of the nearest open x and y position on the racetrack
    """
    # Record number of rows (lines) and columns in the environment
    rows = len(environment)
    cols = len(environment[0])

    # Add expanded coverage for searching for nearest open cell
    max_radius = max(rows, cols)

    # Generate a search radius for each scenario
    for radius in range(max_radius):

        # If car is not moving in y direction
        if vx == 0:
            x_off_range = range(-radius, radius + 1)
        # If the velocity in y-direction is negative
        elif vx < 0:
            # Search in the positive direction
            x_off_range = range(0, radius + 1)
        else:
            # Otherwise search in the negative direction
            x_off_range = range(-radius, 1)

        # For each value in the search radius range of x
        for x_offset in x_off_range:

            # Start near to crash site and work outwards from there
            x = x_crash + x_offset
            y_radius = radius - abs(x_offset)

            # If car is not moving in y direction
            if vy == 0:
                y_range = range(y_crash - y_radius, y_crash + y_radius + 1)
            # If the velocity in y-direction is negative
            elif vy < 0:
                y_range = range(y_crash, y_crash + y_radius + 1)
            # If the velocity in y-direction is positive
            else:
                y_range = range(y_crash - y_radius, y_crash + 1)

            # For each value in the search radius range of y
            for y in y_range:
                # We can't go outside the environment(racetrack) boundary
                if x < 0 or x >= rows:
                    continue
                if y < 0 or y >= cols:
                    continue

                # If we find and open cell, return that (x,y) open cell
                if environment[x][y] in acceptable_cells:
                    return x, y

    # No open grid squares found on the racetrack
    return None, None


def act(old_x, old_y, old_vx, old_vy, accel, environment, deterministic=False):
    """
    This method generates the new state s' (position and velocity) from the old state s and the action a taken by
    the race car.
    :param int old_y: The old y position of the car
    :param int old_x: The old x position of the car
    :param int old_vy: The old y velocity of the car
    :param int old_vx: The old x velocity of the car
    :param tuple accel: (ax,ay) - acceleration in y and x directions
    :param list environment: The racetrack
    :param boolean deterministic: True if we always follow the policy
    :return s' where s' = new_y, new_x, new_vy, and new_vx
    :rtype int
    """
    # This method is deterministic if the same output is returned given
    # the same input information
    if not deterministic:
        # If action fails (car fails to take the prescribed action a)
        if accel[0] != 0 and accel[1] != 0 and random() > PROB_ACCELER_SUCCESS:
            # print("Car failed to accelerate!")
            accel = (0, 0)

    # Using the old velocity values and the new acceleration values,
    # get the new velocity value
    new_vx, new_vy = get_new_velocity((old_vx, old_vy), accel)

    # Using the new velocity values, update with the new positio
    temp_x = old_x + new_vx
    temp_y = old_y + new_vy

    # Find the nearest open cell on the racetrack to this new position
    new_x, new_y = get_nearest_open_cell(environment, temp_x, temp_y, new_vx, new_vy)
    # If a crash happens (i.e. new position is not equal to the nearest
    # open position on the racetrack
    if new_y != temp_y or new_x != temp_x:
        # Velocity of the race car is set to 0 and the car stays where it was
        new_vy, new_vx = 0, 0
        new_y, new_x = old_y, old_x

    # Return the new state
    return new_x, new_y, new_vx, new_vy


def get_policy_from_Q(cols, rows, vel_range, Q):
    """
    This method returns the policy pi(s) based on the action taken in each state that maximizes the value of Q in
    the table Q[s,a]. It returns the best action that the race car should take in each state that
    maximizes the value of Q.
    :return pi : the policy
    :rtype: dictionary: key is the state tuple, value is the action tuple (ax,ay)
    """
    # Create an empty dictionary called pi
    pi = {}

    # For each state s in the environment
    for x in range(rows):
        for y in range(cols):
            for vx in vel_range:
                for vy in vel_range:
                    # Store the best action for each state that maximizes the value of Q.
                    # argmax looks across all actions given a state and returns the index ai of the maximum Q value
                    pi[(x, y, vx, vy)] = ACTIONS[np.argmax(Q[x][y][vx][vy])]
    return pi


def value_iteration_algorithm(environment, reward=REWARD):
    """
    This method is the value iteration algorithm.
    :param list environment: The environment
    :param float reward: The terminal states' reward (i.e. finish line)
    :rtype dictionary
    """
    # Calculate the number of rows and columns of the environment
    rows = len(environment)
    cols = len(environment[0])

    # Create a table V(s) that will store the optimal Q-value for each state. This table will help us determine
    # when we should stop the algorithm and return the output. Initialize all the values of V(s) to arbitrary values,
    # except the terminal state (i.e. finish line state) that has a value of 0. values[x][y][vy][vx]
    values = [[[[random() for _ in VELOCITY_RANGE] for _ in VELOCITY_RANGE] for _ in line] for line in environment]

    # Set the finish line states to 0
    for x in range(rows):
        for y in range(cols):
            # Terminal state has a value of 0
            if environment[x][y] == GOAL:
                for vx in VELOCITY_RANGE:
                    for vy in VELOCITY_RANGE:
                        values[x][y][vx][vy] = reward

    # Initialize all Q(s,a) to arbitrary values, except the terminal state
    # (i.e. finish line states) that has a value of 0. Q[x][y][vx][vy][ai]
    Q = [[[[[random() for _ in ACTIONS] for _ in VELOCITY_RANGE] for _ in VELOCITY_RANGE] for _ in line] for line in
         environment]

    # Set finish line state-action pairs to 0
    for x in range(rows):
        for y in range(cols):
            # Terminal state has a value of 0
            if environment[x][y] == GOAL:
                for vx in VELOCITY_RANGE:
                    for vy in VELOCITY_RANGE:
                        for ai, a in enumerate(ACTIONS):
                            Q[x][y][vx][vy][ai] = reward

    start_time = time.time()
    # This is where we train the agent (i.e. race car). Training entails
    # optimizing the values in the tables of V(s) and Q(s,a)
    for training_iteration in range(NO_TRAINING_ITERATIONS):
        # Keep track of the old V(s) values so we know if we reach stopping
        # criterion
        values_prev = deepcopy(values)

        # When this value gets below the error threshold, we stop training. This is the maximum change of V(s)
        delta = 0.0

        # For all the possible states s in S
        for x in range(rows):
            for y in range(cols):
                for vx in VELOCITY_RANGE:
                    for vy in VELOCITY_RANGE:

                        # If the car crashes into a wall
                        if environment[x][y] == WALL:
                            values[x][y][vx][vy] = HIT_WALL_PENALTY
                            continue

                        # For each action a in the set of possible actions
                        for ai, a in enumerate(ACTIONS):
                            # The reward is -1 for every state except
                            # for the finish line states
                            if environment[x][y] == GOAL:
                                r = reward
                            else:
                                r = STEP_COST

                            # Get the new state s'. s' is based on the current state s and the current action a
                            new_x, new_y, new_vx, new_vy = act(x, y, vx, vy, a, environment, deterministic=True)

                            # V(s'): value of the new state when taking action
                            # a from state s. This is the one step look ahead.
                            value_of_new_state = values_prev[new_x][new_y][new_vx][new_vy]

                            # Get the new state s'. s' is based on the current state s and the action (0,0)
                            new_x, new_y, new_vx, new_vy = act(x, y, vx, vy, (0, 0), environment, deterministic=True)

                            # V(s'): value of the new state when taking acceleration = (0,0) from state s.
                            # This is the value if the race car attempts to accelerate but fails
                            value_of_new_state_if_action_fails = values_prev[new_x][new_y][new_vx][new_vy]

                            # Expected value of the new state s'
                            expected_value = (PROB_ACCELER_SUCCESS * value_of_new_state) + (
                                    PROB_ACCELER_FAILURE * (value_of_new_state_if_action_fails))

                            # Update the Q-value in Q[s,a] with immediate reward + discounted future value
                            Q[x][y][vx][vy][ai] = r + (DISC_RATE * expected_value)

                        # Get the action with the highest Q value
                        argMaxQ = np.argmax(Q[x][y][vx][vy])

                        # Update V(s)
                        values[x][y][vx][vy] = Q[x][y][vx][vy][argMaxQ]

        # Make sure all finish lines have REWARD
        for x in range(rows):
            for y in range(cols):
                if environment[x][y] == GOAL:
                    for vx in VELOCITY_RANGE:
                        for vy in VELOCITY_RANGE:
                            values[x][y][vx][vy] = reward

        # See if the V(s) values are stabilizing find the maximum change of any of the states. Delta is a float.
        delta = max([max([max([max([abs(values[x][y][vx][vy] - values_prev[x][
            y][vx][vy]) for vy in VELOCITY_RANGE]) for vx in (
                                   VELOCITY_RANGE)]) for y in range(cols)]) for x in range(rows)])

        # If the values of each state are stabilized, return the policy and exit this method.
        if delta < ERROR_THRESHOLD or time.time() - start_time >= 600:
            return get_policy_from_Q(cols, rows, VELOCITY_RANGE, Q), training_iteration

    return get_policy_from_Q(cols, rows, VELOCITY_RANGE, Q), NO_TRAINING_ITERATIONS


def start_car_race(environment, policy):
    """
    Race car will do a trial on the race track according to the policy.
    :param list environment: The environment
    :param dictionary policy: A dictionary containing the best action for a given state.
        The key is the state x,y,vx,vy and value is the action (ax,ay) acceleration
    :return i: Total steps to complete race (i.e. from starting position to finish line)
    :rtype int

    """
    environment_display = deepcopy(environment)  # Copy the environment
    starting_pos = get_random_start_position(environment)  # Get a starting position on the race track
    x, y = starting_pos
    vx, vy = 0, 0  # We initialize velocity to 0
    stop_clock = 0  # A variable in order to check if we get stuck

    # Begin time race
    for i in range(MAX_STEPS):
        # Show the race car on the racetrack
        print_environment(environment_display, car_position=[x, y])
        a = policy[(x, y, vx, vy)]  # Get the best action given the current state

        # If we are at the finish line, stop the time trial
        if environment[x][y] == GOAL:
            return i, starting_pos[0], starting_pos[1]

        # Take action and get new a new state s'
        x, y, vx, vy = act(x, y, vx, vy, a, environment)

        # Determine if the car gets stuck
        if vy == 0 and vx == 0:
            stop_clock += 1
        else:
            stop_clock = 0

        # We have gotten stuck as the car has not been moving for 10 time-steps
        if stop_clock == 10:
            return MAX_STEPS, None, None

    # Car made max steps and it did not find the finish line (any F in the environment)
    return MAX_STEPS, None, None


def main():
    print("The race car is training. Please wait...")
    racetrack = read_environment(FILENAME)

    policy, training_iterations = value_iteration_algorithm(racetrack)

    print("Number of Training Iterations: " + str(training_iterations))
    print("Now I'll execute %d races" % NO_RACES)
    time.sleep(5)
    for race_number in range(NO_RACES):
        total_steps, x, y = start_car_race(racetrack, policy)

        if total_steps >= MAX_STEPS:
            print("Car could not find its way to finish line")
        else:
            print("Race %d" % (race_number + 1))
            print("Car started from (%d, %d) took %d steps" % (x, y, total_steps))

        # Until last race:
        if race_number != NO_RACES - 1:
            # Delay
            print("Start new race")
            time.sleep(5)


if __name__ == '__main__':
    main()
