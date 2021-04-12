import socket
import os
import sys

from _thread import *

TIMEOUT = 1
TIMEOUT_RECHARGING = 5
MAX_UNICODE = 65536
HASH_MULTI_CONS = 1000

#zpravy serveru
#pohyb
SERVER_MOVE = "102 MOVE\a\b"
SERVER_TURN_LEFT = "103 TURN LEFT\a\b"
SERVER_TURN_RIGHT = "104 TURN RIGHT\a\b"

SERVER_PICK_UP = "105 GET MESSAGE\a\b"
SERVER_LOGOUT = "106 LOGOUT\a\b"
SERVER_KEY_REQUEST = "107 KEY REQUEST\a\b"
SERVER_OK = "200 OK\a\b"

#errors
SERVER_LOGIN_FAILED = "300 LOGIN FAILED\a\b"
SERVER_SYNTAX_ERROR = "301 SYNTAX ERROR\a\b"
SERVER_LOGIC_ERROR = "302 LOGIC ERROR\a\b"
SERVER_KEY_OUT_OF_RANGE_ERROR = "303 KEY OUT OF RANGE\a\b"

#konstanty serveru
SERVER_CONFIRMATION_MAX_LENGTH = 7


#zpravy klienta
CLIENT_RECHARGING = "RECHARGING"
CLIENT_FULL_POWER = "FULL POWER"

#konstanty klienta
CLIENT_USERNAME_MAX_LENGTH = 18
CLIENT_KEY_ID_MAX_LENGTH = 3
CLIENT_CONFIRMATION_MAX_LENGTH = 5
CLIENT_OK_MAX_LENGTH = 10
CLIENT_RECHARGING_MAX_LENGTH = 10
CLIENT_FULL_POWER_MAX_LENGTH = 10
CLIENT_MESSAGE_MAX_LENGTH = 98

#directions
RIGHT, LEFT, UP, DOWN = (0, 1, 2, 3)

#states
NOT_NAMED, NOT_KEY_ID, WRITING_CONFORMATION, MOVING, TURNING_RIGHT, TURNING_LEFT, GETTING_SECRET = (0, 1, 2, 3, 4, 5, 6)

#(server_key, client_key)
keys = [(23019,32037), (32037, 29295), (18789, 13603), (16443, 29533), (18189, 21952)]


class Error(Exception):
    """abstract error class"""
    pass


class ServerLoginFailed(Error):

    def __init__(self):
        self.error_message = SERVER_LOGIN_FAILED

    def __str__(self):
        return self.error_message


class ServerSyntaxError(Error):

    def __init__(self):
        self.error_message = SERVER_SYNTAX_ERROR

    def __str__(self):
        return self.error_message


class ServerLogicError(Error):

    def __init__(self):
        self.error_message = SERVER_LOGIC_ERROR

    def __str__(self):
        return self.error_message


class ServerKeyOutOfRangeError(Error):

    def __init__(self):
        self.error_message = SERVER_KEY_OUT_OF_RANGE_ERROR

    def __str__(self):
        return self.error_message

class End(Error):
    def __init__(self):
        self.error_message = SERVER_LOGOUT

    def __str__(self):
        return self.error_message


class Client:
    def __init__(self, connection):
        self.name = None
        self.keyID = None
        self.position = None
        self.direction = None
        self.connection = connection
        self.state = NOT_NAMED
        self.is_recharging = False
        self.already_read = ""
        self.avoiding_obstacle = False
        self.obstacle_position = None
        self.move_obs_counter = 0
        self.avd_obs_counter = 3
        self.first_moves = 2
        self.obstacle_at_beginning = 0

    def parse_client_ok(self, data):
        parsed_data = data.split(' ')
        if len(parsed_data) != 3:
            raise ServerSyntaxError()
        if parsed_data[0] != 'OK':
            raise ServerSyntaxError()
        if not parsed_data[1].strip('-').isnumeric() or not parsed_data[2].strip('-').isnumeric():
            raise ServerSyntaxError()
        return [int(parsed_data[1]), int(parsed_data[2])]

    def move(self, data):
        new_position = self.parse_client_ok(data)
        if new_position == self.position:
            self.avoiding_obstacle = True
            self.avd_obs_counter = 3
            if self.position[1] == 0:
                self.move_obs_counter = 2
            else:
                self.move_obs_counter = 1
            self.avoid_obstacle(data)
        else:
            if self.direction == RIGHT:
                self.position[0] += 1
            elif self.direction == LEFT:
                self.position[0] -= 1
            elif self.direction == UP:
                self.position[1] += 1
            elif self.direction == DOWN:
                self.position[1] -= 1
            if new_position != self.position:
                raise ServerSyntaxError()
            if not self.avoiding_obstacle:
                self.move_to_secret()

    def first_move(self, data):
        self.position = self.parse_client_ok(data)
        self.state = MOVING
        self.connection.sendall(str.encode(SERVER_MOVE))

    def get_direction(self, data):
        new_position = self.parse_client_ok(data)
        if self.position[0] > new_position[0]:
            if self.position[1] != new_position[1]:
                raise ServerSyntaxError()
            self.direction = LEFT
            self.position = new_position
        elif self.position[0] < new_position[0]:
            if self.position[1] != new_position[1]:
                raise ServerSyntaxError()
            self.direction = RIGHT
            self.position = new_position
        elif self.position[1] > new_position[1]:
            if self.position[0] != new_position[0]:
                raise ServerSyntaxError()
            self.direction = DOWN
            self.position = new_position
        else:
            if self.position[0] != new_position[0]:
                self.obstacle_at_beginning = 3
                self.solve_obstacle_at_beginning()
            self.direction = UP
            self.position = new_position

    def solve_obstacle_at_beginning(self, data):
        if self.obstacle_at_beginning == 3:
            self.state = TURNING_LEFT
            self.connection.sendall(str.encode(SERVER_TURN_LEFT))
            self.obstacle_at_beginning -= 1
        elif self.obstacle_at_beginning == 2:
            self.turn_left(data)
            self.state = MOVING
            self.connection.sendall(str.encode(SERVER_MOVE))
            self.obstacle_at_beginning -= 1
        else:
            self.get_direction(data)
            self.obstacle_at_beginning -= 1
            self.move_to_secret()

    def turn_left(self, data):
        new_position = self.parse_client_ok(data)
        if new_position != self.position:
            raise ServerSyntaxError()
        if self.direction == RIGHT:
            self.direction = UP
        elif self.direction == LEFT:
            self.direction = DOWN
        elif self.direction == UP:
            self.direction = LEFT
        elif self.direction == DOWN:
            self.direction = RIGHT
        if not self.avoiding_obstacle and self.obstacle_at_beginning == 0:
            self.move_to_secret()

    def turn_right(self, data):
        new_position = self.parse_client_ok(data)
        if new_position != self.position:
            raise ServerSyntaxError()
        if self.direction == RIGHT:
            self.direction = DOWN
        elif self.direction == LEFT:
            self.direction = UP
        elif self.direction == UP:
            self.direction = RIGHT
        elif self.direction == DOWN:
            self.direction = LEFT
        self.move_to_secret()

    def avoid_obstacle(self, mes):
        if self.avd_obs_counter == 3:
            self.state = TURNING_LEFT
            self.connection.sendall(str.encode(SERVER_TURN_LEFT))
            self.avd_obs_counter -= 1
        elif self.avd_obs_counter == 2:
            self.turn_left(mes)
            self.state = MOVING
            self.connection.sendall(str.encode(SERVER_MOVE))
            self.avd_obs_counter -= 1
        elif self.avd_obs_counter == 1:
            self.move(mes)
            self.state = TURNING_RIGHT
            self.connection.sendall(str.encode(SERVER_TURN_RIGHT))
            self.avd_obs_counter -= 1


    def move_to_secret(self):
        if self.move_obs_counter != 0:
            self.state = MOVING
            self.connection.sendall(str.encode(SERVER_MOVE))
            self.move_obs_counter -= 1
            return
        if self.position[1] != 0:
            if self.position[1] < 0:
                if self.direction == UP:
                    self.state = MOVING
                    self.connection.sendall(str.encode(SERVER_MOVE))
                elif self.direction == DOWN:
                    self.state = TURNING_LEFT
                    self.connection.sendall(str.encode(SERVER_TURN_LEFT))
                elif self.direction == LEFT:
                    self.state = TURNING_RIGHT
                    self.connection.sendall(str.encode(SERVER_TURN_RIGHT))
                else:
                    self.state = TURNING_LEFT
                    self.connection.sendall(str.encode(SERVER_TURN_LEFT))
            else:
                if self.direction == UP:
                    self.state = TURNING_LEFT
                    self.connection.sendall(str.encode(SERVER_TURN_LEFT))
                elif self.direction == DOWN:
                    self.state = MOVING
                    self.connection.sendall(str.encode(SERVER_MOVE))
                elif self.direction == LEFT:
                    self.state = TURNING_LEFT
                    self.connection.sendall(str.encode(SERVER_TURN_LEFT))
                else:
                    self.state = TURNING_RIGHT
                    self.connection.sendall(str.encode(SERVER_TURN_RIGHT))
        else:
            if self.position[0] == 0:
                self.state = GETTING_SECRET
                self.connection.sendall(str.encode(SERVER_PICK_UP))
            elif self.position[0] < 0:
                if self.direction == UP:
                    self.state = TURNING_RIGHT
                    self.connection.sendall(str.encode(SERVER_TURN_RIGHT))
                elif self.direction == DOWN:
                    self.state = TURNING_LEFT
                    self.connection.sendall(str.encode(SERVER_TURN_LEFT))
                elif self.direction == LEFT:
                    self.state = TURNING_RIGHT
                    self.connection.sendall(str.encode(SERVER_TURN_RIGHT))
                else:
                    self.state = MOVING
                    self.connection.sendall(str.encode(SERVER_MOVE))
            else:
                if self.direction == UP:
                    self.state = TURNING_LEFT
                    self.connection.sendall(str.encode(SERVER_TURN_LEFT))
                elif self.direction == DOWN:
                    self.state = TURNING_RIGHT
                    self.connection.sendall(str.encode(SERVER_TURN_RIGHT))
                elif self.direction == LEFT:
                    self.state = MOVING
                    self.connection.sendall(str.encode(SERVER_MOVE))
                else:
                    self.state = TURNING_LEFT
                    self.connection.sendall(str.encode(SERVER_TURN_LEFT))


    def get_name(self, data):
        self.name = data
        self.connection.sendall(str.encode(SERVER_KEY_REQUEST))

    def count_hash(self):
        counted_hash = 0
        for c in self.name:
            counted_hash += ord(c)
        counted_hash *= HASH_MULTI_CONS
        counted_hash %= MAX_UNICODE
        return counted_hash

    def get_keyID(self, data):
        if not data.isnumeric():
            raise ServerSyntaxError()
        if int(data) < 0 or int(data) > 4:
            raise ServerKeyOutOfRangeError()
        self.keyID = int(data)

        server_key = keys[self.keyID][0]
        counted_hash = self.count_hash()
        server_hash = (counted_hash + server_key) % MAX_UNICODE
        server_confirmation = str(server_hash) + "\a\b"
        self.connection.sendall(str.encode(server_confirmation))

    def make_authentication(self, data):
        if not data.isnumeric():
            raise ServerSyntaxError()

        counted_hash = self.count_hash()
        client_key = keys[self.keyID][1]
        client_hash = (counted_hash + client_key) % MAX_UNICODE
        if client_hash != int(data):
            raise ServerLoginFailed()
        self.connection.sendall(str.encode(SERVER_OK))
        self.state = MOVING
        self.connection.sendall(str.encode(SERVER_MOVE))

    def check_length(self, data_length):
        if self.is_recharging:
            if data_length > CLIENT_FULL_POWER_MAX_LENGTH:
                raise ServerSyntaxError()
        elif self.state == NOT_NAMED:
            if data_length > CLIENT_USERNAME_MAX_LENGTH:
                raise ServerSyntaxError()
        elif self.state == NOT_KEY_ID:
            if data_length > CLIENT_KEY_ID_MAX_LENGTH:
                raise ServerSyntaxError()
        elif self.state == WRITING_CONFORMATION:
            if data_length > CLIENT_CONFIRMATION_MAX_LENGTH:
                raise ServerSyntaxError()
        elif self.state == MOVING or self.state == TURNING_LEFT or self.state == TURNING_RIGHT:
            if data_length > CLIENT_OK_MAX_LENGTH:
                raise ServerSyntaxError()
        elif self.state == GETTING_SECRET:
            if data_length > CLIENT_MESSAGE_MAX_LENGTH:
                raise ServerSyntaxError()

    def process_parsed_data(self, parsed_data):
        for mes in parsed_data:
            mes_length = len(mes)
            self.check_length(mes_length)
            if self.is_recharging:
                if mes != CLIENT_FULL_POWER:
                    raise ServerLogicError()
                self.is_recharging = False
                self.connection.settimeout(TIMEOUT)
            elif self.avoiding_obstacle and self.avd_obs_counter == 0:
                self.avoiding_obstacle = False
                self.turn_right(mes)
            elif self.avoiding_obstacle:
                self.avoid_obstacle(mes)
            elif self.obstacle_at_beginning != 0:
                self.solve_obstacle_at_beginning(mes)
            elif mes == CLIENT_FULL_POWER:
                raise ServerLogicError()
            elif mes == CLIENT_RECHARGING:
                self.is_recharging = True
                self.connection.settimeout(TIMEOUT_RECHARGING)
            elif self.state == NOT_NAMED:
                self.get_name(mes)
                self.state = NOT_KEY_ID
            elif self.state == NOT_KEY_ID:
                self.get_keyID(mes)
                self.state = WRITING_CONFORMATION
            elif self.state == WRITING_CONFORMATION:
                self.make_authentication(mes)
            elif self.first_moves > 0:
                if self.first_moves == 2:
                    self.first_move(mes)
                    self.first_moves -= 1
                elif self.first_moves == 1:
                    self.get_direction(mes)
                    self.first_moves -= 1
                    self.move_to_secret()
            elif self.state == MOVING:
                self.move(mes)
            elif self.state == TURNING_LEFT:
                self.turn_left(mes)
            elif self.state == TURNING_RIGHT:
                self.turn_right(mes)
            elif self.state == GETTING_SECRET:
                raise End()

    def parse_data(self, data):
        parsed_data = self.already_read + data
        self.already_read = ''
        padding = False
        if '\a\b' not in parsed_data:
            self.already_read = parsed_data
            data_length = len(self.already_read)
            self.check_length(data_length)
            return
        if parsed_data[-2:] != '\a\b':
            padding = True
        parsed_data = parsed_data.split('\a\b')
        if parsed_data[-1] == '':
            parsed_data.pop()
        if padding:
            self.already_read = parsed_data[-1]
            parsed_data.pop()
        self.process_parsed_data(parsed_data)
        return



def multi_threaded_client(connection):
    client = Client(connection)
    #connection.settimeout(TIMEOUT)
    while True:
        try:
            data = connection.recv(2048).decode('utf-8')
            print(data)
            client.parse_data(data)
        except (ServerSyntaxError, ServerLogicError, ServerKeyOutOfRangeError, ServerLoginFailed) as err:
            connection.sendall(str.encode(str(err)))
            break
        except End as end:
            connection.sendall(str.encode(str(end)))
            break
        #except:
        #    break

        if not data:
            break

    connection.close()


def main():
    if len(sys.argv) < 2:
        sys.stderr.write("Neni dostatek argumentu")

    port = int(sys.argv[1])
    host = sys.argv[2]
    thread_counter = 0
    sock = socket.socket()

    #bind
    try:
        sock.bind((host, port))
    except socket.error as e:
        sock.close()
        sys.stderr.write(str(e))

    # listen
    try:
        sock.listen()
    except socket.error as e:
        sock.close()
        sys.stderr.write(str(e))

    # create threads and work
    while True:
        try:
           Robot, address = sock.accept()
           start_new_thread(multi_threaded_client, (Robot,))
           thread_counter += 1
        except:
            break

    # close socket
    sock.close()


if __name__ == "__main__":
    main()