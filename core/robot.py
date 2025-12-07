import time
import RPi.GPIO as GPIO
import threading
import math

class Robot:
    
	def __init__(self):
		# Configure pins
		self.SLP_PIN = 23	# Sleep pin

		AIN1_PIN = 18	# PWM pin for motor direction 1
		AIN2_PIN = 12	# PWM pin for motor direction 2
		self.ENCODER_A1_PIN = 24	# Encoder interrupt pin (you can change this to any available GPIO)
		self.ENCODER_A2_PIN = 25	# Second encoder pin 

		BIN1_PIN = 19	# PWM pin for motor direction 1
		BIN2_PIN = 13	# PWM pin for motor direction 2
		self.ENCODER_B1_PIN = 5	# Encoder interrupt pin for motor B
		self.ENCODER_B2_PIN = 6	# Second encoder pin for motor B
  
		# Encoder variables
		self.pulses_per_revolution = 7	# Adjust this based on your encoder specifications
		self.gearing = 298

		# Wheel variables
		wheel_diameter_cm = 6.5  # Diameter of the wheel in centimeters
		self.wheel_circumference_cm = wheel_diameter_cm * 3.1416  # Circumference = π * d
  
		# Robot wheel width in cm (distance between the two wheels)
		self.wheel_base_cm = 9.525  # 3.75 inches in cm
		self.wheel_base_section_cm = self.wheel_base_cm * 3.1416 / 360  # For turning calculations
		
		# Distance calibration factor to fix measurement accuracy
		# If robot moves 20.4cm instead of 25.4cm, calibration = 25.4/20.4 ≈ 1.245
		# Adjust this value based on actual vs expected distance
		self.distance_calibration_factor = 1.0  # Increase if robot moves too little

		# Control parameters for RPM control
		self.kp = 0.5  # Reduced proportional gain for smoother control
		self.adjustment_threshold = 0.1  # Smaller threshold for more precise control
		self.max_adjustment = 2.0  # Limit maximum duty cycle change per iteration
		self.min_duty_cycle = 70  # Minimum duty cycle to prevent stalling
		self.max_duty_cycle = 100  # Maximum duty cycle
		
		# Synchronization parameters - TUNE THESE TO REDUCE WOBBLE
		self.sync_kp = 1.5  # Increased from 0.3 - more aggressive sync correction
		self.sync_threshold = 0.01  # Reduced from 0.05 - catch even smaller differences
		self.max_sync_adjustment = 1.5  # Limit sync adjustments to prevent overcorrection
		
 		# RPM filtering parameters
		self.alpha = 0.3  # Low-pass filter coefficient (0.1 = heavy filtering, 0.9 = light filtering)
  
  		# Encoder state variables
		self.encoder_count_A = 0
		self.last_time_A = time.time()
		self.rpm_A = 0
		self.rpm_A_filtered = 0  # Filtered RPM for smoother control
		self.dir_A = 1
		self.rpm_lock_A = threading.Lock()

		self.encoder_count_B = 0
		self.last_time_B = time.time()
		self.rpm_B = 0
		self.rpm_B_filtered = 0  # Filtered RPM for smoother control
		self.dir_B = 1
		self.rpm_lock_B = threading.Lock()
  
		# Position control variables
		self.current_pos = (0, 0)  # (x, y) position in cm
		self.current_angle = 0  # Orientation angle in degrees

		self.relative_pos = (0, 0)  # Relative (x, y) position in cm
		self.relative_angle = 0  # Relative orientation angle in degrees
  
		self.current_target_pos = (0, 0)  # Target (x, y) position in cm
		self.current_target_angle = 0  # Target orientation angle in degrees

		self.last_target_pos = (0, 0)
		self.last_target_angle = 0
  
		self.interrupt_flag = False
		self.log_time = time.time()

		# Set GPIO mode
		GPIO.setmode(GPIO.BCM)
		GPIO.setwarnings(False)

		# Setup pins
		GPIO.setup(self.SLP_PIN, GPIO.OUT)

		GPIO.setup(AIN1_PIN, GPIO.OUT)
		GPIO.setup(AIN2_PIN, GPIO.OUT)
		GPIO.setup(self.ENCODER_A1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.ENCODER_A2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

		GPIO.setup(BIN1_PIN, GPIO.OUT)
		GPIO.setup(BIN2_PIN, GPIO.OUT)
		GPIO.setup(self.ENCODER_B1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
		GPIO.setup(self.ENCODER_B2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
  
		GPIO.add_event_detect(self.ENCODER_A1_PIN, GPIO.RISING, callback=self.encoder_callback_A, bouncetime=1)
		GPIO.add_event_detect(self.ENCODER_B1_PIN, GPIO.RISING, callback=self.encoder_callback_B, bouncetime=1)

  		# Create PWM instances
		self.AIN1 = GPIO.PWM(AIN1_PIN, 2000)	# 2kHz frequency
		self.AIN2 = GPIO.PWM(AIN2_PIN, 2000)	# 2kHz frequency

		self.BIN1 = GPIO.PWM(BIN1_PIN, 2000)	# 2kHz frequency
		self.BIN2 = GPIO.PWM(BIN2_PIN, 2000)	# 2kHz frequency

		# Start PWM with 0% duty cycle
		self.AIN1.start(0)
		self.AIN2.start(0)

		self.BIN1.start(0)
		self.BIN2.start(0)

		# Enable DRV8833 (set SLP high)
		GPIO.output(self.SLP_PIN, GPIO.HIGH)

		# Initialize control variables
		self.current_angle_A = 0
		self.current_angle_B = 0
		self.current_duty_A = self.min_duty_cycle  # Start with moderate initial duty cycle
		self.current_duty_B = self.min_duty_cycle  # Start with moderate initial duty cycle
		self.target_rpm = 18  # Target RPM for both motors
  
		self.time = time.time()

	def cleanup(self):
		# Stop PWM
		self.AIN1.stop()
		self.AIN2.stop()
		self.BIN1.stop()
		self.BIN2.stop()
  
		GPIO.output(self.SLP_PIN, GPIO.LOW)  # Disable DRV8833
		GPIO.remove_event_detect(self.ENCODER_A1_PIN)
		GPIO.remove_event_detect(self.ENCODER_B1_PIN)
		# Clean up GPIO
		GPIO.cleanup()
		print("GPIO cleaned up and motors stopped.")
  
	def encoder_callback_A(self, channel):
		# global encoder_count_A, last_time_A, rpm_A, rpm_A_filtered, dir_A, gearing, alpha
		
		# Read ENCODER_A2_PIN to determine direction
		self.dir_A = GPIO.input(self.ENCODER_A2_PIN)
		
		with self.rpm_lock_A:
			self.encoder_count_A += 1
			
			# Calculate RPM every 'pulses_per_revolution' pulses
			if self.encoder_count_A % self.pulses_per_revolution == 0:
				current_time = time.time()
				time_diff = current_time - self.last_time_A
				
				if time_diff > 0:
					# RPM = (60 seconds / time_for_one_revolution)
					rpm_raw = 60.0 / time_diff / self.gearing
					
					# Apply low-pass filter for smoother RPM readings
					if self.rpm_A_filtered == 0:  # First reading
						self.rpm_A_filtered = rpm_raw
					else:
						self.rpm_A_filtered = (self.alpha * rpm_raw) + ((1 - self.alpha) * self.rpm_A_filtered)
					
					self.rpm_A = self.rpm_A_filtered
					self.last_time_A = current_time
				
	def encoder_callback_B(self, channel):
		# global encoder_count_B, last_time_B, rpm_B, rpm_B_filtered, dir_B, gearing, alpha
		
		# Read ENCODER_B2_PIN to determine direction
		self.dir_B = GPIO.input(self.ENCODER_B2_PIN)
		
		with self.rpm_lock_B:
			self.encoder_count_B += 1
			
			# Calculate RPM every 'pulses_per_revolution' pulses
			if self.encoder_count_B % self.pulses_per_revolution == 0:
				current_time = time.time()
				time_diff = current_time - self.last_time_B
				
				if time_diff > 0:
					# RPM = (60 seconds / time_for_one_revolution)
					rpm_raw = 60.0 / time_diff / self.gearing
					
					# Apply low-pass filter for smoother RPM readings
					if self.rpm_B_filtered == 0:  # First reading
						self.rpm_B_filtered = rpm_raw
					else:
						self.rpm_B_filtered = (self.alpha * rpm_raw) + ((1 - self.alpha) * self.rpm_B_filtered)
					
					self.rpm_B = self.rpm_B_filtered
					self.last_time_B = current_time
     
     # Function to get current RPM
	def get_rpm_A(self):
		with self.rpm_lock_A:
			return self.rpm_A
		
	def get_rpm_B(self):
		with self.rpm_lock_B:
			return self.rpm_B
		
	def get_Angle_A(self):
		"""Get angle in degrees (for backward compatibility)"""
		with self.rpm_lock_A:
			return (self.encoder_count_A / self.pulses_per_revolution) * (360 / self.gearing)

	def get_Angle_B(self):
		"""Get angle in degrees (for backward compatibility)"""
		with self.rpm_lock_B:
			return (self.encoder_count_B / self.pulses_per_revolution) * (360 / self.gearing)

	def get_distance_A_cm(self):
		"""Get distance traveled by motor A in centimeters with calibration"""
		with self.rpm_lock_A:
			angle_degrees = (self.encoder_count_A / self.pulses_per_revolution) * (360 / self.gearing)
			return (angle_degrees / 360) * self.wheel_circumference_cm * self.distance_calibration_factor

	def get_distance_B_cm(self):
		"""Get distance traveled by motor B in centimeters with calibration"""
		with self.rpm_lock_B:
			angle_degrees = (self.encoder_count_B / self.pulses_per_revolution) * (360 / self.gearing)
			return (angle_degrees / 360) * self.wheel_circumference_cm * self.distance_calibration_factor

	def move(self, abs_distance_cm, wheel_A_dir=1, wheel_B_dir=1) -> bool:
		# Use calibrated distance measurements
		distance_A_cm = self.get_distance_A_cm()
		distance_B_cm = self.get_distance_B_cm()
		finished = False
		# print(f"Moving: Target Distance = {abs_distance_cm:.2f} cm | Distance A = {distance_A_cm:.2f} cm | Distance B = {distance_B_cm:.2f} cm")
		if self.interrupt_flag:
			# Stop motors
			self.stop()
			self.record_position((distance_A_cm + distance_B_cm) / 2, wheel_A_dir - wheel_B_dir)
			# self.interrupt_flag = False
			return True
		if distance_A_cm < abs_distance_cm or distance_B_cm < abs_distance_cm:
			# Continue moving forward
			# Rotate Motor A
			self.AIN2.ChangeDutyCycle(0 if wheel_A_dir == 1 else self.current_duty_A)
			self.AIN1.ChangeDutyCycle(self.current_duty_A if wheel_A_dir == 1 else 0)
			
			# Rotate Motor B
			self.BIN2.ChangeDutyCycle(0 if wheel_B_dir == 1 else self.current_duty_B)
			self.BIN1.ChangeDutyCycle(self.current_duty_B if wheel_B_dir == 1 else 0)
    
			if time.time() - self.time >= 0.1:  # Adjust every 100ms
				self.time = time.time()
				self.adjust_motor_speeds()
				# print(f"Pos: (x={self.current_pos[0]:.2f} cm, y={self.current_pos[1]:.2f} cm) | Angle: {self.current_angle:.2f} deg")
				# print(f"Distance A: {distance_A_cm:.2f} cm | Distance B: {distance_B_cm:.2f} cm | RPM A: {self.get_rpm_A():.2f} | RPM B: {self.get_rpm_B():.2f} | Duty A: {self.current_duty_A:.2f}% | Duty B: {self.current_duty_B:.2f}%")
				speed_diff = abs(self.get_rpm_A() - self.get_rpm_B())
				# print(f"Speed Difference: {speed_diff:.4f} RPM")
			finished = False
		else:
			# Stop motors
			self.stop()
			self.record_position((distance_A_cm + distance_B_cm) / 2, wheel_A_dir - wheel_B_dir)
			finished = True
		return finished

	def rotate(self, abs_angle_deg) -> bool:
		abs_distance_cm = abs_angle_deg * self.wheel_base_section_cm
		wheel_A_dir = 1 if abs_angle_deg > 0 else -1
		wheel_B_dir = -1 if abs_angle_deg > 0 else 1
		return self.move(abs(abs_distance_cm), wheel_A_dir, wheel_B_dir)

	def record_position(self, displacement, rotation=0):
		# Update current position based on displacement and current angle
		if rotation == 0:
			# Straight movement
			displacement_x = displacement * math.cos(math.radians(self.current_angle))
			displacement_y = displacement * math.sin(math.radians(self.current_angle))
			self.current_pos = (self.current_pos[0] + displacement_x, self.current_pos[1] + displacement_y)
		else:
			# Update current angle for rotation
			angle_change = (-1 if rotation < 0 else 1) * displacement / self.wheel_base_cm * (360 / (3.1416))
			self.current_angle += angle_change
			self.current_angle %= 360  # Keep angle within 0-359 degrees

	def stop(self):
		# Stop Motor A
		self.AIN1.ChangeDutyCycle(0)
		self.AIN2.ChangeDutyCycle(0)
		# Stop Motor B
		self.BIN1.ChangeDutyCycle(0)
		self.BIN2.ChangeDutyCycle(0)
		# Reset encoder counts
		with self.rpm_lock_A:
			# Encoder state variables
			self.encoder_count_A = 0
			self.last_time_A = time.time()
			self.rpm_A = 0
			self.rpm_A_filtered = 0  # Filtered RPM for smoother control
			self.dir_A = 1

			self.encoder_count_B = 0
			self.last_time_B = time.time()
			self.rpm_B = 0
			self.rpm_B_filtered = 0  # Filtered RPM for smoother control
			self.dir_B = 1
    
    
	def adjust_motor_speeds(self):
		current_rpm_A = self.get_rpm_A()
		current_rpm_B = self.get_rpm_B()
		if current_rpm_A > 0:  # Only adjust if we have valid RPM reading for motor A
			# if current_angle_A < 360:
			rpm_error_A = self.target_rpm - current_rpm_A
			if abs(rpm_error_A) > self.adjustment_threshold:
				duty_adjustment_A = rpm_error_A * self.kp
				# Limit the maximum adjustment per iteration for smooth control
				duty_adjustment_A = max(-self.max_adjustment, min(self.max_adjustment, duty_adjustment_A))
				self.current_duty_A += duty_adjustment_A
				self.current_duty_A = max(self.min_duty_cycle, min(self.max_duty_cycle, self.current_duty_A))
		
		if current_rpm_B > 0:  # Only adjust if we have valid RPM reading for motor B
			# if current_angle_B < 360:
			rpm_error_B = self.target_rpm - current_rpm_B
			if abs(rpm_error_B) > self.adjustment_threshold:
				duty_adjustment_B = rpm_error_B * self.kp
				# Limit the maximum adjustment per iteration for smooth control
				duty_adjustment_B = max(-self.max_adjustment, min(self.max_adjustment, duty_adjustment_B))
				self.current_duty_B += duty_adjustment_B
				self.current_duty_B = max(self.min_duty_cycle, min(self.max_duty_cycle, self.current_duty_B))
		
		# Synchronization: Fine-tune to match speeds after individual control
		if current_rpm_A > 0 and current_rpm_B > 0:
			speed_diff = current_rpm_A - current_rpm_B
			if abs(speed_diff) > self.sync_threshold:
				# Apply gentle correction to synchronize speeds
				sync_adjustment = speed_diff * self.sync_kp * 0.5  # Half adjustment to each motor
				
				# Limit sync adjustment to prevent overcorrection
				sync_adjustment = max(-self.max_sync_adjustment, min(self.max_sync_adjustment, sync_adjustment))
				
				# Adjust both motors in opposite directions to meet in the middle
				self.current_duty_A -= sync_adjustment  # Faster motor slows down
				self.current_duty_B += sync_adjustment  # Slower motor speeds up
				
				# Clamp duty cycles
				self.current_duty_A = max(self.min_duty_cycle, min(self.max_duty_cycle, self.current_duty_A))
				self.current_duty_B = max(self.min_duty_cycle, min(self.max_duty_cycle, self.current_duty_B))
    
	def head_to(self, target_x_cm, target_y_cm) -> bool:
		"""Move robot to target position by first rotating to face target, then moving forward"""
		# Calculate distance and angle to target
		delta_x = target_x_cm - self.current_pos[0]
		delta_y = target_y_cm - self.current_pos[1]
		distance_to_target = math.hypot(delta_x, delta_y)
		# 	self.current_target_pos = (target_x_cm, target_y_cm)
		# 	print(f"New target position set: (x={target_x_cm:.2f} cm, y={target_y_cm:.2f} cm)")
		# 	displacement_A_cm = self.get_distance_A_cm()
		# 	displacement_B_cm = self.get_distance_B_cm()
		# Check if we're already at the target
		# print(f"Current Position: (x={self.current_pos[0]:.2f} cm, y={self.current_pos[1]:.2f} cm), Target Position: (x={target_x_cm:.2f} cm, y={target_y_cm:.2f} cm), Distance to Target: {distance_to_target:.2f} cm")
		if distance_to_target < 2.0:  # Within 2cm tolerance
			self.stop()
			# print(f"Reached target position: (x={self.current_pos[0]:.2f} cm, y={self.current_pos[1]:.2f} cm)")
			return True
		
		# Calculate required heading angle
		target_angle = math.degrees(math.atan2(delta_y, delta_x))
		angle_diff = target_angle - self.current_angle
		
		# Normalize angle difference to [-180, 180]
		while angle_diff > 180:
			angle_diff -= 360
		while angle_diff < -180:
			angle_diff += 360
		
		# First phase: Rotate to face target
		if abs(angle_diff) > 3:  # 3 degree tolerance for rotation
			rotation_finished = self.rotate(angle_diff)
			if self.interrupt_flag:
				print("⏸️  Movement interrupted during rotation.")
				# self.interrupt_flag = False
				return True  # Consider interrupted movement as finished for now
			if not rotation_finished:
				# print(f"Rotating {angle_diff:.1f}° to face target. Current angle: {self.current_angle:.1f}°")
				return False  # Still rotating
			else:
				print(f"Rotation complete. Now facing {self.current_angle:.1f}°")
				return False  # Rotation finished, but need to start moving next iteration
		
		# Second phase: Move forward toward target
		move_finished = self.move(distance_to_target)
		if self.interrupt_flag:
			print("⏸️  Movement interrupted during translation.")
			# self.interrupt_flag = False
			return True  # Consider interrupted movement as finished for now
		if not move_finished:
			# print(f"Moving toward target. Distance remaining: {distance_to_target:.1f} cm")
			return False  # Still moving
		else:
			print(f"Movement complete. Position: (x={self.current_pos[0]:.2f}, y={self.current_pos[1]:.2f})")
			return True  # Reached target

	def get_status(self):
		"""Get current robot status for debugging"""
		return {
			'position': self.current_pos,
			'angle': self.current_angle,
			'encoder_A': self.encoder_count_A,
			'encoder_B': self.encoder_count_B,
			'distance_A': self.get_distance_A_cm(),
			'distance_B': self.get_distance_B_cm(),
			'rpm_A': self.get_rpm_A(),
			'rpm_B': self.get_rpm_B()
		}
	
	def print_status(self):
		"""Print current robot status"""
		status = self.get_status()
		print(f"Position: ({status['position'][0]:.2f}, {status['position'][1]:.2f}) cm")
		print(f"Angle: {status['angle']:.1f}°")
		print(f"Distances: A={status['distance_A']:.2f} cm, B={status['distance_B']:.2f} cm")
		print(f"RPMs: A={status['rpm_A']:.1f}, B={status['rpm_B']:.1f}")
	
	def run(self, target, log_interval=1):
		self.current_target_pos = target
		if time.time() - self.log_time >= log_interval:
			self.log_time = time.time()
			self.print_status()
		if self.current_target_pos != self.last_target_pos:
			print(f"New target position set: (x={target[0]:.2f} cm, y={target[1]:.2f} cm)")
			self.interrupt_flag = True
			self.head_to(self.last_target_pos[0], self.last_target_pos[1])
			self.last_target_pos = self.current_target_pos
			self.interrupt_flag = False
		else:
			target_x, target_y = target
			if self.head_to(target_x, target_y):
				# print(f"Waiting for new target...")
				# self.print_status()
				return True
			# self.interrupt_flag = False
		return False


# Example usage
if __name__ == "__main__":
	try:
		robot = Robot()
		
		robot.stop()
		time.sleep(1)  # Give some time to stabilize
  
		print("=== ROBOT HEAD_TO TEST ===")
		robot.print_status()
		print("Starting waypoint navigation...")
		
		sim_time = 0
		current_time = time.time()
		start_time = time.time()
		finished = False
	
		# Define waypoints to visit
		waypoints = [(-20, 0), (20, 0)]
		current_waypoint = 0
		triggered = False
		new_waypoint = (-20, 0)
		
		while True:
			robot.run(new_waypoint)
			if sim_time >= 6:
				new_waypoint = (10, 10)
			if sim_time >= 13:
				new_waypoint = (0, 0)
				
			sim_time = time.time() - start_time
	except KeyboardInterrupt:
		print("Interrupted by user.")
	finally:
		robot.cleanup()
 

				