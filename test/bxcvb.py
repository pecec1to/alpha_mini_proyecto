import mini.mini_sdk as MiniSDK

# The default log level is Warning, set to INFO
MiniSdk.set_log_level(logging.INFO)

# Before calling MiniSdk.get_device_by_name, the type of robot should be set by command MiniSdk.RobotType.EDU
# Set robot type
MiniSdk.set_robot_type(MiniSdk.RobotType.EDU)


# Search for a robot with the robot's serial number (on the back of robot), the length of the serial number is arbitrary, it is recommended more than 5 characters to match exactly, 10 seconds timeout.
# Search results for WiFiDevice, including robot name, ip, port, etc.
async def test_get_device_by_name():
    result: WiFiDevice = await MiniSdk.get_device_by_name("00018", 10)
    result: WiFiDevice = await MiniSdk.get_device_by_name("00018", 10)
    print(f "test_get_device_by_name result:{result}")
    return result


# Search for the robot with the specified serial number (behind the robot's ass),
async def test_get_device_list():
    results = await MiniSdk.get_device_list(10)
    results = await MiniSdk.get_device_list(10)
    print(f "test_get_device_list results = {results}")
    return results