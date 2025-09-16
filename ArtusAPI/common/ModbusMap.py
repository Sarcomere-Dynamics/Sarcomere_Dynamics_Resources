class ModbusMap: # Artus Generic Modbus Map
    def __init__(self):
        self.modbus_reg_map = {
            'command_register': 0,
            'target_position_start_reg': 1,
            'target_torque_start_reg': 50,
            'feedback_register' : 200,
            'feedback_position_start_reg': 201,
            'feedback_torque_start_reg': 250,
            'feedback_temperature_start_reg': 400,
        }