import os
import json

from bot.slot_filling import SlotFilling
from bot.dialogue_management import DialogueManagement
from bot.response_generation import ResponseGeneration


class MessageProcessing:
    """
    Class that manages the processing of user messages.
    """

    def __init__(self):
        """
        Constructor of the MessageProcessing class.
        - Loads the slot_template, the state information, the edge_conditions 
        and the rg_mapping information.
        - Initializes instances of the SlotFilling class, the DialogueManagement
        class, and the Response Generation class. 
        """

        root_path = os.path.join(os.path.dirname(__file__))
        self.slot_template = self.load_slot_template(root_path)
        state_info = self.load_state_info(root_path)
        self.state_info = state_info["states"]
        self.final_state = state_info["final_state"]
        self.edge_conditions = self.load_edge_conditions(root_path)
        self.rg_mapping = self.load_rg_mapping(root_path)

        self.slot_filling = SlotFilling(self.slot_template, self.state_info)
        self.dialogue_management = DialogueManagement(self.state_info, 
                                                      self.edge_conditions,
                                                      self.final_state)
        self.response_generation = ResponseGeneration(self.rg_mapping)
    
    def load_slot_template(self, root_path: str) -> dict:
        """
        Loads the slot_template.json file.
        
        Args: 
            root_path (str): The path of this file. 
        
        Returns:
            str: The slot information from the slot_template.json file as a 
            dictionary. 
        """

        file_path = os.path.join(root_path, "data", "slot_filling", 
                                 "slot_template.json")
        with open(file_path, "r", encoding="utf-8") as f:
            slot_template = json.load(f)["slots"]
        return slot_template
    
    def load_state_info(self, root_path: str) -> dict:
        """
        Loads the states.json file.
        
        Args: 
            root_path (str): The path of this file. 
        
        Returns:
            str: The state information from the slot_template.json file as a 
            dictionary. 
        """

        file_path = os.path.join(root_path, "data", "states", "states.json")
        with open(file_path, "r", encoding="utf-8") as f:
            state_info = json.load(f)
        return state_info
    
    def load_edge_conditions(self, root_path: str) -> dict:
        """
        Loads the edge_conditions.json file.
        
        Args: 
            root_path (str): The path of this file. 
        
        Returns:
            dict: The information from the edge_conditions.json file as a 
            dictionary.
        """

        file_path = os.path.join(root_path, "data", "states", "edge_conditions.json")
        with open(file_path, "r", encoding="utf-8") as f:
            edge_conditions = json.load(f)["edge_conditions"]
        return edge_conditions
    
    def load_rg_mapping(self, root_path: str) -> dict:
        """
        Loads the rg_mapping.json file.
        
        Args: 
            root_path (str): The path of this file. 
        
        Returns:
            dict: The information from the rg_mapping.json file as a dictionary.
        """

        file_path = os.path.join(root_path, "data", "rg_mapping", 
                                 "rg_mapping.json")
        with open(file_path, "r", encoding="utf-8") as f:
            rg_mapping = json.load(f)["rg_mapping"]
        return rg_mapping

    def process_message(
        self,
        user_text: str,
        treatment_group: int,
        conversation_history: list,
        dialogue_state_history: list,
        slot_filling: dict
    ) -> tuple[str, str, bool, dict]:
        """
        Manages the processing of user messages.
        This function contains the pipeline for processing user messages. 

        Args:
            user_text (str): The user message to process.
            treatment_group (int): The treatment group value.
            conversation_history (list): The conversation history.
            dialogue_state_histpry (list): The dialogue state history.
            slot_filling (dict): The slot filling dictionary. 

        Returns:
            tuple[str, str, bool, dict]: A tuple with the bot's response, the 
            new dialogue state, a flag whether the final state has been reached 
            and the updated slot filling dictionary. 
        """

        # Extract the current dialogue state
        current_dialogue_state = dialogue_state_history[-1] 

        # Perform the slot filling
        try:
            newly_filled_slots = self.slot_filling.run(
                user_text=user_text,
                current_dialogue_state=current_dialogue_state,
                conversation_history=conversation_history
            )
        except:
            newly_filled_slots = self.slot_filling.run_fallback(
                user_text=user_text,
                current_dialogue_state=current_dialogue_state
            )

        # Update the slot filling dictionary
        for slot, value in newly_filled_slots.items():
            if slot not in slot_filling:
                slot_filling[slot] = value
        
        # Perform the dialogue management
        try:
            new_dialogue_state, rg_action, final_state = self.dialogue_management.run(
                current_dialogue_state=current_dialogue_state,
                slot_filling=slot_filling,
                newly_filled_slots=newly_filled_slots
            )
        except:
            new_dialogue_state, rg_action, final_state = self.dialogue_management.run_fallback(
                current_dialogue_state=current_dialogue_state
            )

        # Perform the response generation
        try:
            bot_response = self.response_generation.run(
                user_text=user_text,
                rg_action=rg_action,
                treatment_group=treatment_group,
                conversation_history=conversation_history,
            )
        except:
            bot_response = self.response_generation.run_fallback(
                rg_action=rg_action,
                treatment_group=treatment_group,
            )

        return bot_response, new_dialogue_state, final_state, slot_filling
