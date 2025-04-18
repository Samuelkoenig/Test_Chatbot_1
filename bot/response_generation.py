import os
from dotenv import load_dotenv
import openai
from openai import OpenAI
        

class ResponseGeneration:
    """
    Class that performs the response generation.
    """

    def __init__(self, rg_mapping: dict):
        """
        Constructor of the ResponseGeneration class.
        - Initializes the rg_mapping dictionary.
        - Creates a class variable for the root path of this file. 
        - Creates an openai client instance.

        Args:
            rg_mapping (dict): The dictionary with the response generation 
            mapping.
        """

        self.rg_mapping = rg_mapping
        self.root_path = os.path.join(os.path.dirname(__file__))
        self.openai_client = self.create_openai_client()
    
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

    def run(self, user_text: str, rg_action: str, treatment_group: int, conversation_history: list) -> str:
        """
        Performs the response generation.
        - Generates a developer prompt and a user prompt for the gpt api. 
        Uses the developer prompt and user prompt templates from the 
        rg_prompts folder and fills the variables (expecially the contents for 
        the bot's responses and the conversation history) with the respective
        values, taking into account the rg_action and the conversation history.
        - Uses the prompts to generate the bot's response using the gpt api.
        
        Args: 
            user_text (str): The user message to be answered.
            rg_action (str): The action to be performed.
            treatment_group (int): The treatment group value.
            conversation_history (list): The conversation history. 
            
        Returns:
            str: The bot's response.
        """

        # Transform the conversation history in a suitable format for the 
        # prompt
        conv_hist_for_prompt = self._get_conv_hist_for_prompt(
            conversation_history, user_text, lastx=4)

        # Complie the developer prompt
        rg_dev_prompt = self._get_rg_dev_prompt(rg_action, treatment_group)

        # Compile the user prompt
        rg_user_prompt = self._get_rg_user_prompt(rg_action, treatment_group, 
                                                 conv_hist_for_prompt)

        # Call the gpt api to perform the response generation task
        gpt_response = self._call_gpt_api(rg_dev_prompt, rg_user_prompt)

        # Prepare the gpt api results to be outputted as a chatbot message
        bot_response = self._verify_gpt_response(gpt_response)

        return bot_response
    
    def _get_conv_hist_for_prompt(self, conversation_history: dict, user_text: str, lastx: int=None) -> str:
        """
        Converts the conversation history to a format suitable for the prompt.

        Args: 
            conversation_history (list): The conversation history. 
            user_text (str): The user message to be answered.
            lastx (int/None): How many messages to consider when preparing the 
            conversation history: Only the last x messages are considered.

        Returns: 
            str: The conversation history in a suitable format for the prompt. 
        """

        # Extract onlx the messages from the conversation history to be 
        # considered
        conversation_history = conversation_history + [("user", user_text)]
        if lastx is not None:
            conversation_history = conversation_history[-lastx:]

        # Transform the conversation history to a suitable string format
        lines = []
        for role, text in conversation_history:
            speaker = "Chatbot" if role.lower() == "bot" else "Kunde"
            lines.append(f'{speaker}: "{text}"')
        conv_hist_string = "\n".join(lines)

        return conv_hist_string
    
    def _get_rg_dev_prompt(self, action: str, treatment_group: str) -> str:
        """
        Complies the developer prompt for the gpt api.
        
        Args: 
            action (str): The action to be performed.
            treatment_group (int): The treatment group value.
        
        Returns: 
            str: The developer prompt for the response generation.
        """

        # Load the developer prompt template for the experimental treatment
        dev_file_suffix = "empathetic" if treatment_group == 1 else "neutral"
        dev_file_name = f"developer_prompt_{dev_file_suffix}.txt"
        rg_dev_path_suffix = ["data", "rg_prompts", dev_file_name]
        rg_dev_prompt_template = self.load_prompt_template(self.root_path, 
                                                           rg_dev_path_suffix)
        
        # Load the developer prompt variable content
        var_file_name = self.rg_mapping[action]["dev_prompt_variable"]
        var_path_suffix = ["data", "rg_prompts", "dev_variants", var_file_name]
        dev_prompt_variable = self.load_prompt_template(self.root_path, 
                                                        var_path_suffix)
        
        # Complete the developer prompt by filling the variables
        rg_dev_prompt = rg_dev_prompt_template.format(
            dev_prompt_variable=dev_prompt_variable
        )

        return rg_dev_prompt
    
    def _get_rg_user_prompt(self, action: str, treatment_group: int, conv_hist_for_prompt: str) -> str:
        """
        Compiles the user prompt for the gpt api.
        
        Args:
            action (str): The action to be performed.
            treatment_group (int): The treatment group value.
            conv_hist_for_prompt (dict): The conversation history in a string 
            format to be inserted into the user prompt.
        
        Returns:
            str: The user prompt for the response generation.
        """

        # Load the user prompt template
        user_file_suffix = "empathetic" if treatment_group == 1 else "neutral"
        user_file_name = f"user_prompt_{user_file_suffix}.txt"
        rg_user_path_suffix = ["data", "rg_prompts", user_file_name]
        rg_user_prompt_template = self.load_prompt_template(self.root_path, 
                                                            rg_user_path_suffix)
        
        # Load the user prompt variable content
        var_file_name = self.rg_mapping[action]["user_prompt_content"]
        var_path_suffix = ["data", "rg_prompts", "user_contents", var_file_name]
        user_prompt_variable = self.load_prompt_template(self.root_path, 
                                                        var_path_suffix)
        
        # Complete the user prompt by filling the variables
        rg_dev_prompt = rg_user_prompt_template.format(
            conversation_history=conv_hist_for_prompt,
            user_prompt_content=user_prompt_variable
        )

        return rg_dev_prompt
    
    def _call_gpt_api(self, developer_prompt: str, user_prompt: str, model: str = "gpt-4o") -> str:
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
            temperature=1,
            #max_tokens=300,
        )

        # Extract api response
        response = completion.choices[0].message.content
        return response

    def _verify_gpt_response(self, gpt_response: str) -> str:
        """
        Verifies that the gpt_response is in a chatbot message format.
        
        Args:
            gpt_response (str): The gpt api response.
        
        Returns:
            str: The response for the chatbot message.
        """
        
        return gpt_response
    
    def run_fallback(self, rg_action: str, treatment_group: int) -> str:
        """
        Fallback function for the response generation.
        - This function is called if an exception occurred during the execution 
        of the run function.
        - Loads a canned chatbot response based on the rg_action and the 
        treatment group value.

        Args: 
            rg_action (str): The action to be performed.
            treatment_group (int): The treatment group value.

        Returns: 
            str: The bot's canned response.
        """

        # Configure file path components
        treatment = "empathetic" if treatment_group == 1 else "neutral"
        var_file_name = self.rg_mapping[rg_action]["user_prompt_content"]

        # Load canned response
        root_path = self.root_path
        path_suffix_parts = [
            "data", "canned_responses", treatment, var_file_name
        ]
        canned_response = self.load_prompt_template(root_path, path_suffix_parts)

        return canned_response
