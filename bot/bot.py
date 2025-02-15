import os
import json
from dotenv import load_dotenv
import time

import openai

from botbuilder.core import ActivityHandler, TurnContext, ConversationState
from botbuilder.schema import ChannelAccount


class Bot(ActivityHandler):
    """
    Class that represents the chatbot.
    """

    def __init__(self, conversation_state: ConversationState, treatment_fallback: int):
        """
        Constructor of the Bot class. 
        - Specifies the state variables of a bot instance: 
            - welcome_state: Specifies whether a bot instance is in the welcome state.
            - treatment_state: Specifies whether a bot instance should be treated as treatment or control group.
            - history_state: The conversation history. 
            - dialogue_state: The current state of the dialogue. 
        - Initializes an instance of the DialogueLogic class to generate the bot's messages. 
        
        Args: 
            conversation_state (ConversationState): The stored conversation state.
            treatment_fallback (int): Fallback value if no treatmentGroup provided in channel_data.
        """

        self.conversation_state = conversation_state
        self.treatment_fallback = treatment_fallback

        self.welcome_state_accessor = self.conversation_state.create_property("WelcomeState")
        self.treatment_state_accessor = self.conversation_state.create_property("TreatmentGroup")
        self.history_state_accessor = self.conversation_state.create_property("HistoryState")
        self.dialogue_state_accessor = self.conversation_state.create_property("DialogueState")

        self.conversation_logic = DialogueLogic()

    async def set_treatment_group(self, turn_context: TurnContext):
        """
        Stores the treatment group value in the conversation state. 
        - Stores the treatmentGroup if provided in channel_data, otherwise uses the treatment_fallback value.

        Args: 
            turn_context (TurnContext): The information about the current activity.
        """

        # Receive channel data
        channel_data = turn_context.activity.channel_data if turn_context.activity.channel_data else {}

        # If the value in self.treatment_state_accessor is None or not existant, 
        # get the treatmentGroup value from channel_data. 
        treatment_group = await self.treatment_state_accessor.get(turn_context, None)
        print("Existing treatment value: ", treatment_group)
        if treatment_group == None: 
            treatment_group = channel_data.get("treatmentGroup", None)
            if treatment_group is None:
                treatment_group = self.treatment_fallback
            else:
                try:
                    treatment_group = int(treatment_group)
                except ValueError:
                    treatment_group = self.treatment_fallback
            await self.treatment_state_accessor.set(turn_context, treatment_group)
            print("Treatment group: ", treatment_group)

        await self.conversation_state.save_changes(turn_context)
    
    async def on_conversation_update_activity(self, turn_context: TurnContext):
        """
        Handle conversationUpdate activities. 
        - This function is called before on_members_added_activity.
        - Stores the treatmentGroup if provided, otherwise uses the treatment_fallback value.

        Args: 
            turn_context (TurnContext): The information about the current activity.
        """
        
        await self.set_treatment_group(turn_context)

        return await super().on_conversation_update_activity(turn_context)
    
    async def on_members_added_activity(self, members_added: ChannelAccount, turn_context: TurnContext):
        """
        Initializes a new conversation. 
        - Sends the welcome message using the DialogueLogic class instance. 
        - Updates the conversation history. 
        - Updates the dialogue state. 
        - Switches the welcome_state variable. 

        Args: 
            members_added (ChannelAccount): The information about the user account. 
            turn_context (TurnContext): The information about the current activity.
        """

        await self.set_treatment_group(turn_context)

        # Retrieve welcome state
        welcome_sent = await self.welcome_state_accessor.get(turn_context, False)

        # Receive and specify treatment state
        treatment_group = await self.treatment_state_accessor.get(turn_context, self.treatment_fallback)

        # Generate initial welcome message
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id and not welcome_sent:
                conversation_history = await self.history_state_accessor.get(turn_context)
                dialogue_states = await self.dialogue_state_accessor.get(turn_context)
                if conversation_history is None:
                    conversation_history = []
                if dialogue_states is None:
                    dialogue_states = []
                
                welcome_text, new_dialogue_states = self.conversation_logic.get_welcome_message(
                    treatment_group,
                    dialogue_states
                )
                conversation_history.append(("bot", welcome_text))
                await turn_context.send_activity(welcome_text)
                
                await self.dialogue_state_accessor.set(turn_context, new_dialogue_states)
                await self.history_state_accessor.set(turn_context, conversation_history)
                await self.welcome_state_accessor.set(turn_context, True)
                await self.conversation_state.save_changes(turn_context)

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Processes user messages.
        - Sends the bot response using the DialogueLogic class instance. 
        - Updates the conversation history. 
        
        Args:
            turn_context (TurnContext): The information about the current activity.
        """

        treatment_group = await self.set_treatment_group(turn_context)
        
        channel_data = turn_context.activity.channel_data if turn_context.activity.channel_data else {}
        treatment_group = channel_data.get("treatmentGroup", None)
        if treatment_group is None:
            treatment_group = self.treatment_fallback
        else:
            try:
                treatment_group = int(treatment_group)
            except ValueError:
                treatment_group = self.treatment_fallback

        user_text = turn_context.activity.text
        conversation_history = await self.history_state_accessor.get(turn_context)
        dialogue_states = await self.dialogue_state_accessor.get(turn_context)
        if conversation_history is None:
            conversation_history = []
        if dialogue_states is None:
            dialogue_states = []

        bot_response, new_dialogue_states = self.conversation_logic.get_bot_message(
            treatment_group,
            conversation_history,
            dialogue_states,
            user_text
        )

        conversation_history.append(("user", user_text))
        conversation_history.append(("bot", bot_response))
        await turn_context.send_activity(bot_response + str(treatment_group))

        await self.dialogue_state_accessor.set(turn_context, new_dialogue_states)
        await self.history_state_accessor.set(turn_context, conversation_history)
        await self.conversation_state.save_changes(turn_context)


class DialogueLogic:
    """
    Class that contains the logic for generating the bot's messages.
    """

    def __init__(self): 
        """
        Constructor of the DialogueLogic class. 
        Initializes a dictionary with the dialogue states. 
        Loads the gpt api key from the environment variables. 
        """

        self.dialogue_states = {}
        self.load_dialogue_states()

        load_dotenv()
        openai.api_key = os.getenv("OPENAI_API_KEY")
        self.openai_client = openai.OpenAI()
    
    def load_dialogue_states(self):
        """
        Loads the dialogue states from the json file. 
        """

        dialogue_states_file_path = os.path.join(os.path.dirname(__file__), "dialogue_states.json")
        with open(dialogue_states_file_path, "r", encoding="utf-8") as f:
            self.dialogue_states = json.load(f)

    def get_welcome_message(self, treatment_group: int, dialogue_states_history: list) -> tuple[str, list]:
        """
        Returns the welcome message based on the treatment_group value. 
        Updates the dialogue_states_history.

        Args: 
            treatment_group (int): The treatment group value. 
            dialogue_states_history (list): The previous dialogue states of the conversation. 

        Returns:
            str: The bot's welcome message. 
            list: The updated dialogue states history of the conversation. 
        """
        
        new_dialogue_states_history = self.determine_next_dialogue_state(dialogue_states_history)
        bot_welcome_message = self.dialogue_states[new_dialogue_states_history[-1]]["message"]

        return bot_welcome_message, new_dialogue_states_history

    def get_bot_message(self, treatment_group: int, conversation_history: list, dialogue_states_history: list, user_text: str) -> tuple[str, list]:
        """
        Returns a bot response to a user message based on the treatment group value and the conversation history. 

        Args: 
            treatment_group (int): The treatment group value. 
            conversation_history (list): The previous messages of the conversation. 
            dialogue_states_history (list): The previous dialogue states of the conversation. 
            user_text (str): The current user message to be answered. 

        Returns:
            str: The bot's response to the user message. 
            list: The updated dialogue states history of the conversation.  
        """

        new_dialogue_states_history = self.determine_next_dialogue_state(dialogue_states_history, conversation_history, user_text)
        bot_message = self.dialogue_states[new_dialogue_states_history[-1]]["message"]

        if treatment_group == 1: 
            start_time = time.perf_counter()
            bot_message = self.get_empathetic_response(conversation_history, user_text, bot_message)
            end_time = time.perf_counter() 
            execution_time = end_time - start_time
            print(f"Execution time for the gpt api call: {execution_time:.6f} seconds")
        else: 
            time.sleep(1.3)

        return bot_message, new_dialogue_states_history
    
    def determine_next_dialogue_state(self, dialogue_states_history: list, conversation_history: list = [], user_text: str = "") -> list:
        """
        Determines the next dialogue state based on the dialogue state history, 
        the conversation history and the user message.

        Args: 
            dialogue_states_history (list): The previous dialogue states of the conversation. 
            conversation_history (list): The previous messages of the conversation. 
            user_text (str): The current user message to be answered. 
        
        Returns: 
            list: The updated dialogue states history of the conversation.
        """

        if len(dialogue_states_history) == 0:
            dialogue_states_history.append("1")
        elif dialogue_states_history[-1] == "1":
            dialogue_states_history.append("3")
        elif dialogue_states_history[-1] == "3":
            dialogue_states_history.append("5")
        elif dialogue_states_history[-1] == "5":
            dialogue_states_history.append("7")
        elif dialogue_states_history[-1] == "7":
            dialogue_states_history.append("9")
        else: 
            dialogue_states_history.append("9")

        return dialogue_states_history
    
    def get_empathetic_response(self, conversation_history: list, user_text: str, bot_message: str) -> str: 
        """
        Formulates a response by the chatbot in an empathetic way using the GPT model.
        
        Args: 
            conversation_history (list): The previous messages of the conversation. 
            user_text (str): The current user message to be answered. 
            bot_message (str): The bot message that should be formulated in an empathetic way. 
        
        Returns: 
            str: The bot response, formulated in an empathetic way. 
        """

        root_path = os.path.join(os.path.dirname(__file__))

        developer_prompt_file_path = root_path + "/prompts/empathetic_response_prompt/developer_prompt.txt"
        with open(developer_prompt_file_path, "r", encoding="utf-8") as f_dev:
            developer_prompt = f_dev.read()

        user_prompt_file_path = root_path + "/prompts/empathetic_response_prompt/user_prompt.txt"        
        with open(user_prompt_file_path, "r", encoding="utf-8") as f_user:
            user_prompt_template = f_user.read()
        
        conv_hist_string = self.get_conv_hist_for_prompt(conversation_history, user_text)

        user_prompt = user_prompt_template.format(
            conversation_history=conv_hist_string,
            bot_message=bot_message
        )

        print(developer_prompt)
        print(user_prompt)

        completion = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "developer", "content": developer_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )

        print(completion)

        empathetic_response = completion.choices[0].message.content

        return empathetic_response
    
    def get_conv_hist_for_prompt(self, conversation_history: list, user_text: str) -> str: 
        """
        Takes the conversation_history and converts it into a string suitable for the GPT API prompt.
        
        Args: 
            conversation_history (list): The previous messages of the conversation. 
            user_text (str): The current user message to be answered. 
            
        Returns: 
            str: The conversation history in a suitable format for the prompt.
        """

        lines = []
        for role, text in conversation_history:
            if role.lower() == "bot":
                speaker = "Chatbot"
            else:
                speaker = "Kunde"
            lines.append(f'{speaker}: "{text}"')

        lines.append(f'Kunde: "{user_text}"')

        conv_hist_string = "\n".join(lines)
        return conv_hist_string
        
        
