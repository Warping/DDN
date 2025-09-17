import time
from broadcast_controller import BroadcastHandler
from drone_packet import DronePacket
import random

class StateController:
    def __init__(self):
        # self.states = ["SEEKING", "CONNECTED", "MASTER", "SLAVE"]
        self.current_state = "SEEKING"
        self.boot_time = time.monotonic()
        self.last_ping_time = time.monotonic()
        self.drone_id = 0
        self.destination_id = -1  # -1 means broadcast to all
        self.detected_drones = []  # Start with ID 0 detected
        self.acked_drones = []
        self.detected_drones_to_check = []
        self.bh = BroadcastHandler()
        self.time_step = 3  # Time step in seconds
        # self.random_offset = random.uniform(-1, 1)  # Random offset between -1 and 1 seconds
    
    def switch_states(self, new_state):
        print(f"Switching state from {self.current_state} to {new_state} : Drone ID {self.drone_id}")
        self.current_state = new_state
        
    def control_loop(self):
        pack_sent_time = time.monotonic()
        display_time = time.monotonic()
        connected_tries = 0
        print("Starting control loop...")
        while True:
            current_time = time.monotonic()
            self.process_incoming()
            if (self.current_state in ["SEEKING", "CONNECTED"]) and \
                (current_time - pack_sent_time) > (1  + random.uniform(-0.02, 0.02)) * self.time_step:
                DronePacket().ping(self.bh, drone_id=self.drone_id, destination_id=self.destination_id, current_state=self.current_state)
                pack_sent_time = time.monotonic()
                print(f"{pack_sent_time} Sending ping from drone {self.drone_id} to {"ALL" if self.destination_id == -1 else self.destination_id}")
                print(f"Current detected drones: {self.detected_drones}")
                print(f"Current drone ID: {self.drone_id}")
                print(f"Current state: {self.current_state}")
                if self.current_state == "CONNECTED":
                    connected_tries += 1
                    if connected_tries > 5:
                        print("No response after 5 tries, resetting to SEEKING state")
                        self.switch_states("SEEKING")
                        self.detected_drones = [self.drone_id]  # Reset detected drones to only include self
                        self.destination_id = -1  # Reset to broadcast
                        connected_tries = 0
            elif self.current_state == "MASTER" and (current_time - pack_sent_time) > (1  + random.uniform(-0.02, 0.02)) * self.time_step:
                self.detected_drones = self.acked_drones.copy()
                self.acked_drones = [self.drone_id]  # Clear acked drones list before sending update
                DronePacket().update(self.bh, drone_id=self.drone_id, destination_id=-1, current_state=self.current_state, update_info={"detected_drones": self.detected_drones})
                pack_sent_time = time.monotonic()
                print(f"{pack_sent_time} Sending update from MASTER drone {self.drone_id} to ALL")
            if self.current_state == "SLAVE" and (current_time - self.last_ping_time > 3 * self.time_step):
                print("No response for 0.5 seconds, resetting to SEEKING state")
                self.switch_states("SEEKING")
                self.detected_drones = [self.drone_id]  # Reset detected drones to only include self
                self.destination_id = -1  # Reset to broadcast
                # Optionally, you could also reset the drone_id here if desired
                # self.drone_id = 0
                self.last_ping_time = time.monotonic()
            # if current_time - display_time > 2:
            #     display_time = time.monotonic()
            #     print("----- Status Update -----")
            #     print(f"Current detected drones: {self.detected_drones}")
            #     print(f"Current drone ID: {self.drone_id}")
            #     print(f"Current state: {self.current_state}")
            # if (current_time - self.last_ping_time) > 1 and max(self.detected_drones) != self.drone_id:
            #     self.last_ping_time = time.monotonic()
            #     print("No response resetting to SEEKING state")
            #     self.current_state = "SEEKING"
            #     self.detected_drones = [self.drone_id]  # Reset detected drones to only include self
            #     # Optionally, you could also reset the drone_id here if desired
            #     # self.drone_id = 0
                
                    
    def process_incoming(self):
        packet_info = self.bh.get_packet()
        last_state = self.current_state
        if packet_info:
            rcv_time, data, packet = packet_info
            try:
                other = DronePacket(data.decode('utf-8'))
                if other.destination_id == -1 or other.destination_id == self.drone_id:
                    self.last_ping_time = time.monotonic()
                    # print(f"Received packet from drone {drone_packet.drone_id} with action {drone_packet.request_action}")
                    # Process the packet based on its action and current state
                    if self.current_state == "SEEKING" and other.request_action == "PING":
                        if self.drone_id == other.drone_id:
                            print(f"Collision detected for drone ID: {self.drone_id}")
                            self.drone_id = other.drone_id + 1
                            print(f"New drone ID assigned: {self.drone_id}")
                        self.detected_drones.append(other.drone_id)
                        self.detected_drones.append(self.drone_id)
                        self.detected_drones = list(set(self.detected_drones))  # Remove duplicates
                        self.destination_id = other.drone_id  # Reply directly to the sender
                        self.switch_states("CONNECTED")
                    elif self.current_state == "CONNECTED" and other.current_state == "CONNECTED" and other.request_action == "PING":
                        print(f"Both drones in CONNECTED state!")
                        if self.drone_id == other.destination_id and self.drone_id < other.drone_id:
                            self.switch_states("MASTER")
                            # print(f"Transitioning to MASTER state with drone ID: {self.drone_id}")
                            print(f"Sending SET_SLAVE to drone ID: {other.drone_id}")
                            DronePacket().set_slave(self.bh, drone_id=self.drone_id, destination_id=other.drone_id, current_state=self.current_state)
                    elif other.request_action == "SET_SLAVE" and other.current_state == "MASTER" and other.destination_id == self.drone_id:
                        self.switch_states("SLAVE")
                        self.destination_id = other.drone_id  # Set destination to MASTER
                        print(f"Transitioning to SLAVE state from with drone ID: {self.drone_id}")
                        print(f"Updated detected drones: {self.detected_drones}")
                    elif other.request_action == "PING" and self.current_state == "MASTER":
                        print(f"Received PING from drone ID: {other.drone_id}")
                        if other.drone_id not in self.detected_drones:
                            self.detected_drones.append(other.drone_id)
                            self.detected_drones = list(set(self.detected_drones))  # Remove duplicates
                            print(f"Updated detected drones: {self.detected_drones}")
                            new_id = other.drone_id
                            print(f"Assigning existing ID {new_id} to drone ID: {other.drone_id}")
                            DronePacket().set_slave(self.bh, drone_id=self.drone_id, destination_id=other.drone_id, current_state=self.current_state)
                        else:
                            print(f"Drone ID: {other.drone_id} already in detected drones.")
                            max_id = max(self.detected_drones)
                            new_id = max_id + 1
                            print(f"Assigning new ID {new_id} to drone ID: {other.drone_id}")
                            self.detected_drones.append(new_id)
                            self.detected_drones = list(set(self.detected_drones))  # Remove duplicates
                            print(f"Updated detected drones: {self.detected_drones}")
                            DronePacket().set_id(self.bh, drone_id=self.drone_id, destination_id=other.drone_id, current_state=self.current_state, new_id=new_id)
                    elif other.request_action == "SET_ID" and other.destination_id == self.drone_id:
                        new_id = other.params.get("new_id", None)
                        if new_id is not None:
                            print(f"Changing drone ID from {self.drone_id} to {new_id}")
                            self.drone_id = new_id
                            if self.current_state != "MASTER":
                                self.switch_states("SLAVE")
                                self.destination_id = other.drone_id  # Reply directly to the sender
                                self.detected_drones = [self.drone_id]  # Reset detected drones to only include self
                                print(f"New drone ID: {self.drone_id}")
                                print(f"Updated detected drones: {self.detected_drones}")
                        # DronePacket().ping(self.bh, drone_id=self.drone_id, destination_id=other.drone_id, current_state=self.current_state)
                    elif other.request_action == "UPDATE" and self.current_state == "SLAVE":
                        update_info = other.params
                        new_drones = update_info.get("detected_drones", [])
                        self.detected_drones = new_drones
                        self.detected_drones = list(set(self.detected_drones))  # Remove duplicates
                        print(f"Received UPDATE from MASTER. Updated detected drones: {self.detected_drones}")
                        print(f"Current drone ID: {self.drone_id}")
                        DronePacket().ack(self.bh, drone_id=self.drone_id, destination_id=other.drone_id, current_state=self.current_state, ack_info={"status": "UPDATE_RECEIVED"})
                    elif other.request_action == "ACK" and self.current_state == "MASTER":
                        print(f"Received ACK from drone ID: {other.drone_id} with info: {other.params}")
                        status = other.params.get("status", "")
                        if status == "UPDATE_RECEIVED":
                            print(f"Slave drone ID: {other.drone_id} acknowledged the update.")
                            self.acked_drones.append(other.drone_id)
                            self.acked_drones = list(set(self.acked_drones))  # Remove duplicates
                            print(f"Current acked drones: {self.acked_drones}")
                            print(f"Current drone ID: {self.drone_id}")
                            
                            

                        
            except Exception as e:
                print(f"Error processing incoming packet: {e}")