# Motor Test for Raspberry Pi Zero with DRV8833 Motor Driver
# Motor 1: PWM GPIO 18 (AIN1) and PWM GPIO 12 (AIN2)
# SLP: GPIO 23
# Encoder: GPIO 24 (interrupt pin)

import time
import RPi.GPIO as GPIO
import threading

# Configure pins
SLP_PIN = 23	# Sleep pin

AIN1_PIN = 18	# PWM pin for motor direction 1
AIN2_PIN = 12	# PWM pin for motor direction 2
ENCODER_A1_PIN = 24	# Encoder interrupt pin (you can change this to any available GPIO)
ENCODER_A2_PIN = 25	# Second encoder pin 

BIN1_PIN = 19	# PWM pin for motor direction 1
BIN2_PIN = 13	# PWM pin for motor direction 2
ENCODER_B1_PIN = 5	# Encoder interrupt pin for motor B
ENCODER_B2_PIN = 6	# Second encoder pin for motor B 

# Encoder variables
pulses_per_revolution = 7	# Adjust this based on your encoder specifications
gearing = 298

# Wheel variables
wheel_diameter_cm = 6.5  # Diameter of the wheel in centimeters
wheel_circumference_cm = wheel_diameter_cm * 3.1416  # Circumference = π * d

encoder_count_A = 0
last_time_A = time.time()
rpm_A = 0
rpm_A_filtered = 0  # Filtered RPM for smoother control
dir_A = 1
rpm_lock_A = threading.Lock()

encoder_count_B = 0
last_time_B = time.time()
rpm_B = 0
rpm_B_filtered = 0  # Filtered RPM for smoother control
dir_B = 1
rpm_lock_B = threading.Lock()

# RPM filtering parameters
alpha = 0.3  # Low-pass filter coefficient (0.1 = heavy filtering, 0.9 = light filtering)

# Set GPIO mode
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)

# Setup pins
GPIO.setup(SLP_PIN, GPIO.OUT)

GPIO.setup(AIN1_PIN, GPIO.OUT)
GPIO.setup(AIN2_PIN, GPIO.OUT)
GPIO.setup(ENCODER_A1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ENCODER_A2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

GPIO.setup(BIN1_PIN, GPIO.OUT)
GPIO.setup(BIN2_PIN, GPIO.OUT)
GPIO.setup(ENCODER_B1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ENCODER_B2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Encoder interrupt callback function
def encoder_callback_A(channel):
	global encoder_count_A, last_time_A, rpm_A, rpm_A_filtered, dir_A, gearing, alpha
	
	# Read ENCODER_A2_PIN to determine direction
	dir_A = GPIO.input(ENCODER_A2_PIN)
	
	with rpm_lock_A:
		encoder_count_A += 1
		
		# Calculate RPM every 'pulses_per_revolution' pulses
		if encoder_count_A % pulses_per_revolution == 0:
			current_time = time.time()
			time_diff = current_time - last_time_A
			
			if time_diff > 0:
				# RPM = (60 seconds / time_for_one_revolution)
				rpm_raw = 60.0 / time_diff / gearing
				
				# Apply low-pass filter for smoother RPM readings
				if rpm_A_filtered == 0:  # First reading
					rpm_A_filtered = rpm_raw
				else:
					rpm_A_filtered = (alpha * rpm_raw) + ((1 - alpha) * rpm_A_filtered)
				
				rpm_A = rpm_A_filtered
				last_time_A = current_time
				
def encoder_callback_B(channel):
	global encoder_count_B, last_time_B, rpm_B, rpm_B_filtered, dir_B, gearing, alpha
	
	# Read ENCODER_B2_PIN to determine direction
	dir_B = GPIO.input(ENCODER_B2_PIN)
	
	with rpm_lock_B:
		encoder_count_B += 1
		
		# Calculate RPM every 'pulses_per_revolution' pulses
		if encoder_count_B % pulses_per_revolution == 0:
			current_time = time.time()
			time_diff = current_time - last_time_B
			
			if time_diff > 0:
				# RPM = (60 seconds / time_for_one_revolution)
				rpm_raw = 60.0 / time_diff / gearing
				
				# Apply low-pass filter for smoother RPM readings
				if rpm_B_filtered == 0:  # First reading
					rpm_B_filtered = rpm_raw
				else:
					rpm_B_filtered = (alpha * rpm_raw) + ((1 - alpha) * rpm_B_filtered)
				
				rpm_B = rpm_B_filtered
				last_time_B = current_time
				
# Setup encoder interrupt (trigger on rising edge)
GPIO.add_event_detect(ENCODER_A1_PIN, GPIO.RISING, callback=encoder_callback_A, bouncetime=1)
GPIO.add_event_detect(ENCODER_B1_PIN, GPIO.RISING, callback=encoder_callback_B, bouncetime=1)

# Function to get current RPM
def get_rpm_A():
	with rpm_lock_A:
		return rpm_A
	
def get_rpm_B():
	with rpm_lock_B:
		return rpm_B
	
def get_Angle_A():
	with rpm_lock_A:
		return (encoder_count_A / pulses_per_revolution) * (360 / gearing)

def get_Angle_B():
	with rpm_lock_B:
		return (encoder_count_B / pulses_per_revolution) * (360 / gearing)

# Create PWM instances
AIN1 = GPIO.PWM(AIN1_PIN, 2000)	# 2kHz frequency
AIN2 = GPIO.PWM(AIN2_PIN, 2000)	# 2kHz frequency

BIN1 = GPIO.PWM(BIN1_PIN, 2000)	# 2kHz frequency
BIN2 = GPIO.PWM(BIN2_PIN, 2000)	# 2kHz frequency

# Start PWM with 0% duty cycle
AIN1.start(0)
AIN2.start(0)

BIN1.start(0)
BIN2.start(0)

# Enable DRV8833 (set SLP high)
GPIO.output(SLP_PIN, GPIO.HIGH)

# Loop forever
try:
	print("Motor test with RPM monitoring started. Press Ctrl+C to stop.")
	print("Encoder connected to GPIO", ENCODER_A1_PIN)
	print("Pulses per revolution:", pulses_per_revolution)
	print("-" * 50)
	
	
	# Control parameters for RPM control
	kp = 0.5  # Reduced proportional gain for smoother control
	adjustment_threshold = 0.1  # Smaller threshold for more precise control
	max_adjustment = 2.0  # Limit maximum duty cycle change per iteration
	min_duty_cycle = 70  # Minimum duty cycle to prevent stalling
	max_duty_cycle = 100  # Maximum duty cycle
	
	# Synchronization parameters - TUNE THESE TO REDUCE WOBBLE
	sync_kp = 1.5  # Increased from 0.3 - more aggressive sync correction
	sync_threshold = 0.01  # Reduced from 0.05 - catch even smaller differences
	max_sync_adjustment = 1.5  # Limit sync adjustments to prevent overcorrection
	
	print("=== WOBBLE TUNING GUIDE ===")
	print("Watch the 'Speed Diff' value - target: < 0.05")
	print("If wobble persists:")
	print("  1. Decrease sync_threshold (try 0.01)")
	print("  2. Increase sync_kp (try 1.0, 1.5)")
	print("  3. Adjust max_sync_adjustment (try 0.5 or 1.5)")
	print("If it becomes unstable:")
	print("  1. Decrease sync_kp (try 0.5)")
	print("  2. Increase sync_threshold (try 0.05)")
	print("=============================\n")
 
	current_angle_A = get_Angle_A()
	current_angle_B = get_Angle_B()
	current_duty_A = min_duty_cycle  # Start with moderate initial duty cycle
	current_duty_B = min_duty_cycle  # Start with moderate initial duty cycle
	target_rpm = 18  # Target RPM for both motors

 
	current_time = time.time()
	dir_A = 0 # Stopped
	dir_B = 0 # Stopped
	
	while current_angle_A < 360 or current_angle_B < 360:
		# Rotate Motor A
		if current_angle_A >= 360:
			AIN1.ChangeDutyCycle(0)
			AIN2.ChangeDutyCycle(0)
		else:
			AIN2.ChangeDutyCycle(0)
			AIN1.ChangeDutyCycle(current_duty_A)
		
		# Rotate Motor B
		if current_angle_B >= 360:
			BIN2.ChangeDutyCycle(0)
			BIN1.ChangeDutyCycle(0)
		else:
			BIN2.ChangeDutyCycle(0)
			BIN1.ChangeDutyCycle(current_duty_B)
		
		# Individual RPM control for each motor to target 12 RPM
		if time.time() - current_time >= 0.05:  # Update every 0.2 seconds
			current_time = time.time()
			# Get current measurements
			current_angle_A = get_Angle_A()
			current_angle_B = get_Angle_B()
			current_rpm_A = get_rpm_A()
			current_rpm_B = get_rpm_B()
			if current_rpm_A > 0:  # Only adjust if we have valid RPM reading for motor A
				if current_angle_A < 360:
					rpm_error_A = target_rpm - current_rpm_A
					if abs(rpm_error_A) > adjustment_threshold:
						duty_adjustment_A = rpm_error_A * kp
						# Limit the maximum adjustment per iteration for smooth control
						duty_adjustment_A = max(-max_adjustment, min(max_adjustment, duty_adjustment_A))
						current_duty_A += duty_adjustment_A
						current_duty_A = max(min_duty_cycle, min(max_duty_cycle, current_duty_A))
			
			if current_rpm_B > 0:  # Only adjust if we have valid RPM reading for motor B
				if current_angle_B < 360:
					rpm_error_B = target_rpm - current_rpm_B
					if abs(rpm_error_B) > adjustment_threshold:
						duty_adjustment_B = rpm_error_B * kp
						# Limit the maximum adjustment per iteration for smooth control
						duty_adjustment_B = max(-max_adjustment, min(max_adjustment, duty_adjustment_B))
						current_duty_B += duty_adjustment_B
						current_duty_B = max(min_duty_cycle, min(max_duty_cycle, current_duty_B))
			
			# Synchronization: Fine-tune to match speeds after individual control
			if current_rpm_A > 0 and current_rpm_B > 0 and current_angle_A < 360 and current_angle_B < 360:
				speed_diff = current_rpm_A - current_rpm_B
				if abs(speed_diff) > sync_threshold:
					# Apply gentle correction to synchronize speeds
					sync_adjustment = speed_diff * sync_kp * 0.5  # Half adjustment to each motor
					
					# Limit sync adjustment to prevent overcorrection
					sync_adjustment = max(-max_sync_adjustment, min(max_sync_adjustment, sync_adjustment))
					
					# Adjust both motors in opposite directions to meet in the middle
					current_duty_A -= sync_adjustment  # Faster motor slows down
					current_duty_B += sync_adjustment  # Slower motor speeds up
					
					# Clamp duty cycles
					current_duty_A = max(min_duty_cycle, min(max_duty_cycle, current_duty_A))
					current_duty_B = max(min_duty_cycle, min(max_duty_cycle, current_duty_B))
			
			print(f"	(A) Angle: {current_angle_A:6.1f} deg | (B) Angle: {current_angle_B:6.1f} deg")
			print(f"	(A) RPM: {current_rpm_A:6.1f} | (B) RPM: {current_rpm_B:6.1f} | Duty A: {current_duty_A:.1f}% | Duty B: {current_duty_B:.1f}%")
			
			# Enhanced status for tuning
			speed_diff = current_rpm_A - current_rpm_B
			sync_active = "SYNC" if abs(speed_diff) > sync_threshold else "OK  "
			print(f"	Target: {target_rpm} | Speed Diff: {speed_diff:+.3f} [{sync_active}] | Err A: {current_rpm_A - target_rpm:+.1f} | Err B: {current_rpm_B - target_rpm:+.1f}")


except KeyboardInterrupt:
	print("\nStopping motor test...")

finally:
	# Clean up GPIO
	distance_A = get_Angle_A() / 360 * wheel_circumference_cm
	distance_B = get_Angle_B() / 360 * wheel_circumference_cm
	print(f"Distance traveled by Motor A: {distance_A:.2f} cm | {distance_A / 2.54:.2f} inches")
	print(f"Distance traveled by Motor B: {distance_B:.2f} cm | {distance_B / 2.54:.2f} inches")
	AIN1.stop()
	AIN2.stop()
	BIN1.stop()
	BIN2.stop()
	GPIO.output(SLP_PIN, GPIO.LOW)	# Disable DRV8833
	GPIO.remove_event_detect(ENCODER_A1_PIN)	# Remove interrupt
	GPIO.remove_event_detect(ENCODER_B1_PIN)	# Remove interrupt
	GPIO.cleanup()
	print("GPIO cleanup complete")
	# print(f"Total encoder pulses recorded: {encoder_count_A}")
	# print(f"Final RPM: {get_rpm_A():.1f}")