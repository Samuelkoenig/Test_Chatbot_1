import random
import os
import json
import re
from dotenv import load_dotenv
import openai
from openai import OpenAI


class SlotFilling:
    """
    Class to perform the slot filling.
    """

    def __init__(self, slot_template: dict, state_info: dict):
        """
        Constructor of the SlotFilling class.
        - Initializes the slot_template dictionary and the state_info dictionary. 
        - Creates an openai client instance.
        - Complies the patterns from the slot_template dictionary to regex 
        patterns using the compile_regex_patterns method.

        Args:
            slot_template (dict): The dictionary with the slot template.
            state_info (dict): The dictionary with the state information. 
        """

        self.slot_template = slot_template
        self.state_info = state_info
        self.openai_client = self.create_openai_client()
        self.slot_patterns = self.compile_regex_patterns()
    
    def create_openai_client(self) -> OpenAI:
        """
        Creates an openai api client.
        - Loads the gpt api key from the environment variables and initializes an openai client. 
        
        Returns:
            OpenAI: The openai client instance.
        """

        try: 
            load_dotenv()
            openai.api_key = os.getenv("OPENAI_API_KEY")
            openai_client = openai.OpenAI()
            return openai_client
        except: 
            return None
    
    def load_prompt_template(self, root_path: str, path_suffix_parts: list) -> str:
        """
        Loads a prompt template in .txt format.
        
        Args: 
            root_path (str): The root file path.
            path_suffix_parts (list): The remaining file path, where the 
            remaining parts are provided as strings in a list.
            
        Returns: 
            str: The prompt template that has been loaded.
        """

        file_path = os.path.join(root_path, *path_suffix_parts)
        with open(file_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
        return prompt_template

    def run(self, user_text: str, current_dialogue_state: str, conversation_history: list) -> dict:
        """
        Performs the slot filling task.
        - Uses the current dialogue state to get the relevant slots to check.
        - Creates a developer and a user prompt for the gpt api based on the 
        slot filling prompt templates (the .txt files in the data/slot_filling) 
        folder. Completes the user prompt template with the last bot message, 
        the user message to analyze and the slots with their descriptions which 
        are relevant in the current dialogue state. 
        - Performs the classification task for each relevant slot using the gpt
        model.
        - Prepares the gpt response for the output format.
        
        Args:
            user_text (str): The user message.
            current_dialogue_state (str): The current dialogue state.
            conversation_history (list): The conversation_history.
            
        Returns:
            dict: The filled slots from the user message. Keys are the ids of 
            the filled slots, values are 1. 
        """

        # Get the relevant slots to analyze based on the current dialogue state
        slots_to_check = self._get_slots_to_check(current_dialogue_state)

        # Extract the last bot message from the conversation history
        last_bot_message = self._get_last_bot_message(conversation_history)

        # Create the prompts for the gpt model
        developer_prompt, user_prompt = self._get_slot_filling_prompts(
            last_bot_message=last_bot_message,
            user_text=user_text,
            slots_to_check=slots_to_check
        )

        # Call the gpt api to perform the slot filling task
        gpt_response = self._call_gpt_api(developer_prompt, user_prompt)

        # Extract the classification results from the gpt response
        classification_result = self._extract_gpt_response(gpt_response, slots_to_check)

        # Prepare the classification results for the output format
        filled_slots = self._prepare_result(classification_result)

        return filled_slots
    
    def _get_slots_to_check(self, current_dialogue_state: str) -> list:
        """
        Determines the slots to be checked for the current state (including 
        validation slots).

        Args:
            current_dialogue_state (str): The current state of the dialogue. 

        Returns: 
            list: A list with all slots to check. 
        """
        
        # Extract base slots for the current dialogue state
        current_state_dict = self.state_info.get(current_dialogue_state, {})
        base_slots = current_state_dict.get("slots_to_check", [])

        # Generate a list with all relevant base slots including validation slots
        slots_to_check = []
        for slot_id in base_slots:
            slots_to_check.append(slot_id)
            validation_slot = self.slot_template[slot_id].get("validation_slot")
            if validation_slot:
                slots_to_check.append(validation_slot)

        return slots_to_check
    
    def _get_last_bot_message(self, conversation_history: list) -> str:
        """
        Extracts the last bot message from the conversation history.
        - If there is no message from the bot in the conversation history, 
        returns an empty string.

        Args:
            conversation_history (list): The conversation history.

        Returns:
            str: The last bot mesage.
        """

        last_bot_message = ""
        for speaker, text in reversed(conversation_history):
            if speaker == "bot":
                last_bot_message = text
                break
        return last_bot_message
    
    def _get_slot_filling_prompts(self, last_bot_message: str, user_text: str, slots_to_check: list) -> tuple[str, str]:
        """
        Builds the gpt prompts for the slot filling task.
        - Loads the developer prompt and the user prompt template.
        - Prepares the relevant slots and their descriptions for the prompt in 
        the format {"slot_id": "slot_description", ...}.
        - Prepares validation slot notes, stating that if a slot is 0,
        its validation slot must also be 0. 
        - Prepares an example output for the relevant slots.
        - Completes the user prompt template with the last bot message, the user 
        message, the relevant slots and their descriptions, the validation slot 
        notes, and an output example with the relevant slots. 

        Args: 
            last_bot_message (str): The last message from the chatbot.
            user_text (str): The user message to classify.
            slots_to_check (list): A list with the slots to check, containing 
            the slot_id values.

        Returns: 
            tuple[str, str]: The developer prompt and the user prompt. 
        """

        # Load prompt templates
        root_path = os.path.join(os.path.dirname(__file__))
        dev_path_suffix = ["data", "slot_filling", "developer_prompt.txt"]
        user_path_suffix = ["data", "slot_filling", "user_prompt_template.txt"]
        developer_prompt = self.load_prompt_template(root_path, dev_path_suffix)
        user_prompt_template = self.load_prompt_template(root_path, user_path_suffix)

        # Prepare the relevant slots with the description
        slots_section = []
        for slot_id in slots_to_check:
            slot_info = self.slot_template[slot_id]
            prompt_desc = slot_info.get("prompt_description", "")
            slots_section.append(f'"{slot_id}": "{prompt_desc}"')
        slots_as_string = "{\n  " + ",\n  ".join(slots_section) + "\n}"

        # Prepare the validation slot note
        validation_slot_notes = ""
        for slot_id in slots_to_check:
            if "_val" in slot_id:
                corresponding_slot = f'"{slot_id.rsplit("_val", 1)[0]}"'
                note = f'\n    - Hinweis: Falls Slot {corresponding_slot} 0 ist, muss Slot "{slot_id}" auch 0 sein.'
                validation_slot_notes += note

        # Prepare an output example
        output_example_as_string = self.prepare_output_example(slots_to_check)

        # Complete the user prompt by filling the variables
        user_prompt = user_prompt_template.format(
            last_bot_message=last_bot_message,
            user_text=user_text,
            slots=slots_as_string,
            validation_slot_notes=validation_slot_notes,
            output_example=output_example_as_string
        )

        return developer_prompt, user_prompt
    
    def prepare_output_example(self, slots_to_check: list) -> str:
        """
        Prepares an example output for the relevant slots.
        - Takes into account that if a slot is 0, its validation slot must also 
        be 0.
        - Take into account that two opposing slots are not 1 at the same time.

        Args:
            slots_to_check (list): A list with the slots to check, containing 
            the slot_id values.

        Returns: 
            str: The example output in string format. 
        """

        # Prepare an output example
        output_example = {}
        for slot_id in slots_to_check:
            if "_val" in slot_id: # Incorporate validation slot condition
                try:
                    if output_example[slot_id.rsplit("_val", 1)[0]] == 1:
                        output_example[slot_id] = random.randint(0, 1)
                    else:
                        output_example[slot_id] = 0
                except KeyError:
                    output_example[slot_id] = 0
            else:
                output_example[slot_id] = random.randint(0, 1)
        
        # Incorporate counterpart condition
        for slot_id in random.sample(slots_to_check, len(slots_to_check)): 
            counterpart_slot = self.slot_template[slot_id].get("counterpart_slot")
            if counterpart_slot and counterpart_slot in slots_to_check: 
                if output_example[counterpart_slot] == output_example[slot_id]:
                    if len(slots_to_check) == 2:
                        output_example[slot_id] ^= 1
                    else:
                        if output_example[slot_id] == 1:
                            output_example[slot_id] = 0

        output_example_as_string = json.dumps(output_example)
        return output_example_as_string
    
    def _call_gpt_api(self, developer_prompt: str, user_prompt: str, model: str = "gpt-4.1") -> str:
        """
        Calls the gpt api.
        - Usees the developer prompt and the user_prompt strings.
        - Returns the api response.

        Args:
            developer_prompt (str): The developer prompt for the gpt api.
            user_prompt (str): The user prompt for the gpt api. 
            model (str): The gpt model to use. 

        Returns:
            str: The gpt api response.
        """

        # Perform the gpt api call
        completion = self.openai_client.chat.completions.create(
            model=model, 
            messages=[
                {"role": "developer", "content": developer_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.0,
            #max_tokens=300,
        )

        # Extract api response
        response = completion.choices[0].message.content
        return response

    def _extract_gpt_response(self, gpt_response: str, slots_to_check: list) -> dict:
        """
        Extracts the gpt response.

        Args:
            gpt_response (str): The gpt generated text (desirably in a jason structure).
            slots_to_check (list): List with all the slots to be checked. 

        Returns:
            dict: The mapping of 0 or 1 for each relevant slot. 
        """

        try:
            parsed = json.loads(gpt_response)
            result = {}
            
            for slot_id in slots_to_check:
                if slot_id in parsed:
                    try:
                        result[slot_id] = int(parsed[slot_id])
                    except (ValueError, TypeError):
                        result[slot_id] = 0    #TODO: Error Handling
                else:
                    result[slot_id] = 0        #TODO: Error Handling
            return result
        
        except Exception:
            return {slot_id: (1 if i == 0 else 0) for i, slot_id in enumerate(slots_to_check)}  #TODO: Error Handling
    
    def _prepare_result(self, classification_result: dict) -> dict:
        """
        Prepares the classification result for the output format.
        - Verifies the validation slot condition: Verifies that there is no case 
        in the classification output where a slot is 0 but its validation slot 
        is 1. If there is such a case, flips the validation slot value to 0.
        - Creates an output dictionary containing only the filled slots. 

        Args: 
            classification_result (dict): The classification result as a 
            mapping of 0 or 1 for each relevant slot.

        Returns:
            dict: The verified classification result. 
        """

        # Verify the validation condition
        for slot_id, val in classification_result.items():
            validation_slot = self.slot_template[slot_id].get("validation_slot")
            if validation_slot:
                if val == 0:
                    classification_result[validation_slot] = 0

        # Create an output dictionary contining only filled slots
        filled_slots = {slot: 1 for slot, val in classification_result.items() if val == 1}

        return filled_slots
    
    def run_fallback(self, user_text: str, current_dialogue_state: str) -> dict:
        """
        Fallback slot filling function.
        - This function is called if an exception occurred during the execution 
        of the run function.
        - Uses the current dialogue state to get the relevant slots to check.
        - Checks the relevant slot in the user text using a pattern matching 
        approach.
        
        Args:
            user_text (str): The user message.
            current_dialogue_state (str): The current dialogue state.
            
        Returns:
            dict: The filled slots from the user message. Keys are the ids of 
            the filled slots, values are 1. 
        """

        # Generate a base dictionary for the filled slots
        filled_slots = {slot_id: 0 for slot_id in self.slot_template.keys()}

        # Get the relevant slots to analyze based on the current dialogue state
        slots_to_check = self._get_slots_to_check(current_dialogue_state)

        # Perform the pattern matching and fill the filled_slots dictionary
        for slot in slots_to_check:
            for pattern in self.slot_patterns[slot]:
                match = pattern.search(user_text)
                if match: 
                    filled_slots[slot] = 1
                    break
        
        # Prepare the filled slots for the output format
        filled_slots = self._prepare_result(filled_slots)

        return filled_slots
    
    def compile_regex_patterns(self):
        """
        Complies the patterns from the slot_template dictionary to regex 
        patterns.

        Returns:
            dict: A dictionary with the slot_ids as keys and a list with the
            corresponding regex patterns as values.
        """

        slot_patterns = {}
        for slot_id, slot_data in self.slot_template.items():
            compiled_list = []
            for pattern_str in slot_data["slot_patterns"]:
                compiled_list.append(re.compile(pattern_str, re.IGNORECASE))
            slot_patterns[slot_id] = compiled_list
        return slot_patterns
