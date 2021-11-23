from ..Script import Script


class TimeLapseCommand(Script):
    def __init__(self):
        super().__init__()

    def getSettingDataString(self):
        return """{
            "name": "Time Lapse Command",
            "key": "TimeLapseCommand",
            "metadata": {},
            "version": 2,
            "settings":
            {
                "enable_trigger_command":
                {
                    "label": "Триггерная команда",
                    "description": "Включить триггерную команду используемую для спуска затвора камеры.",
                    "type": "bool",
                    "default_value": true
                },
				"trigger_command":
                {
                    "label": "Триггерная команда камеры",
                    "description": "Команда G-кода используемая для спуска затвора камеры.",
                    "type": "str",
                    "default_value": "M240",
					"enabled": "enable_trigger_command"
                },
                "trigger_pause_length":
                {
                    "label": "Длина паузы",
                    "description": "Как долго ждать (в мс) после срабатывания камеры.",
                    "type": "int",
                    "default_value": 2000,
                    "minimum_value": 0,
                    "unit": "ms",
					"enabled": "enable_trigger_command"
                },
                "park_print_head":
                {
                    "label": "Парковка печатающей головки",
                    "description": "Включить парковку печатающей головки.",
                    "type": "bool",
                    "default_value": false
                },
                "head_park_x":
                {
                    "label": "Парковка по X",
                    "description": "В какую точку X перемещается голова для фото.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 0,
					"minimum_value": 0,
                    "enabled": "park_print_head"
                },
                "head_park_y":
                {
                    "label": "Парковка по Y",
                    "description": "В какую точку Y перемещается голова для фото.",
                    "unit": "mm",
                    "type": "float",
                    "default_value": 205,
					"minimum_value": 0,
                    "enabled": "park_print_head"
                },
				"park_feed_rate":
                {
                    "label": "Скорость перемещения",
                    "description": "Как быстро голова движется к координатам парковки.",
                    "unit": "mm/s",
                    "type": "float",
                    "default_value": 9000,
					"minimum_value": 0,
                    "enabled": "park_print_head"
                },
				"enable_retraction":
                {
                    "label": "Откат пластика",
                    "description": "Включить откат пластика.",
                    "type": "bool",
                    "default_value": false
                }
            }
        }"""

    def execute(self, data):
        #Активация настроек
        enable_trigger_command = self.getSettingValueByKey("enable_trigger_command")
        park_print_head = self.getSettingValueByKey("park_print_head")
        enable_retraction = self.getSettingValueByKey("enable_retraction")
        #Триггер
        trigger_command = self.getSettingValueByKey("trigger_command")
        trigger_pause_length = self.getSettingValueByKey("trigger_pause_length")
        #Парковка
        x_park = self.getSettingValueByKey("head_park_x")
        y_park = self.getSettingValueByKey("head_park_y")
        park_feed_rate = self.getSettingValueByKey("park_feed_rate")

        gcode_to_append = ""
        gcode_to_append_retract = ""
        gcode_to_append_retract_back = ""
        last_x = 0
        last_y = 0
        last_z = 0
        last_g10 = 0

        if enable_retraction:
            gcode_to_append_retract += self.putValue(G = 10) + " ;Firmware retract\n"
            gcode_to_append_retract_back += self.putValue(G = 11) + " ;Firmware retract\n"

        if park_print_head:
            gcode_to_append += self.putValue(G=1, F=park_feed_rate,X=x_park, Y=y_park) + " ;Park print head\n"
            gcode_to_append += self.putValue(M=400) + " ;Wait for moves to finish\n"

        if enable_trigger_command:
            gcode_to_append += trigger_command + " ;Snap Photo\n"
            gcode_to_append += self.putValue(G=4, P=trigger_pause_length) + " ;Wait for camera\n"

        for idx, layer in enumerate(data):
            lines = layer.split("\n")
            for index, line in enumerate(lines):
                if self.getValue(line, "G") in {0, 1}:  # Track X,Y location.
                    last_x = self.getValue(line, "X", last_x)
                    last_y = self.getValue(line, "Y", last_y)
                if self.getValue(line, "Z"):
                    last_z = index
                if self.getValue(line, "G") in {10}:
                        last_g10 = index

            for line in lines:
                if ";LAYER:" in line:
                    # собрать заново layer
                    layer = ""
                    for index, line in enumerate(lines):
                        if park_print_head:
                            if index <= last_z:
                                layer += line + "\n"
                            else:
                                break
                        else:
                            layer += line + "\n"
                    # добавить команды
                    layer += ";TimeLapse Begin\n"
                    if enable_retraction:
                        if (last_z - last_g10) > 2 or (last_z - last_g10) == 0:
                            layer += gcode_to_append_retract
                    layer += gcode_to_append
                    if park_print_head:
                        layer += self.putValue(G=0, X=last_x, Y=last_y) + "; Restore position \n"
                        layer += self.putValue(M=400) + " ;Wait for moves to finish\n"
                    if enable_retraction:
                        if (last_z - last_g10) > 2 or (last_z - last_g10) == 0:
                            layer += gcode_to_append_retract_back
                            
                    data[idx] = layer
        return data