import os
import json

class DialogueStart:
    """
    Class that manages the welcome message and the state initialization.
    """

    def __init__(self):
        """
        Constructor of the DialogueStart class.
        - Loads the initial_state.json file.
        - Loads the welcome_message.txt file.
        """

        root_path = os.path.join(os.path.dirname(__file__))
        self.initial_state = self.load_initial_state(root_path)
        self.welcome_message = self.load_welcome_message(root_path)
    
    def load_initial_state(self, root_path: str) -> str:
        """
        Loads the initial_state.json file and extracts the initial state value.
        
        Args: 
            root_path (str): The path of this file. 
        
        Returns:
            str: The initial state, read in from the initial_state.json file. 
        """

        file_path = os.path.join(root_path, "data", "dialogue_start", "initial_state.json")
        with open(file_path, "r", encoding="utf-8") as f:
            initial_state_data = json.load(f)
        initial_dialogue_state = str(initial_state_data.get("initial_dialogue_state", "0"))
        return initial_dialogue_state

    def load_welcome_message(self, root_path: str) -> str:
        """
        Loads the welcome_message.txt file and extracts the bot's welcome message.

        Args: 
            root_path (str): The path of this file. 
        
        Returns:
            str: The bot's welcome message, read from the welcome_message.txt file. 
        """

        file_path = os.path.join(root_path, "data", "dialogue_start", "welcome_message.txt")
        with open(file_path, "r", encoding="utf-8") as f:
            welcome_message = f.read()
        return welcome_message
    
    def start_dialogue(self) -> tuple[str, str]:
        """
        Returns the bot's welcome message and the initial dialogue state.
        
        Returns: 
            tuple[str, str]: A tuple containing the bot's welcome message and the initial dialogue state.
        """

        return self.welcome_message, self.initial_state
        