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
        - Initializes an instance of the ConversationLogic class to generate the bot's messages. 
        
        Args: 
            conversation_state (ConversationState): The stored conversation state.
            treatment_fallback (int): Fallback value if no treatmentGroup provided in channel_data.
        """

        self.conversation_state = conversation_state
        self.treatment_fallback = treatment_fallback

        self.welcome_state_accessor = self.conversation_state.create_property("WelcomeState")
        self.treatment_state_accessor = self.conversation_state.create_property("TreatmentGroup")
        self.history_state_accessor = self.conversation_state.create_property("HistoryState")

        self.conversation_logic = ConversationLogic()
    
    async def on_conversation_update_activity(self, turn_context: TurnContext):
        """
        Handle conversationUpdate activities. 
        - This function is called before on_members_added_activity.
        - Used to store the treatmentGroup if provided, otherwise uses the treatment_fallback value.

        Args: 
            turn_context (TurnContext): The information about the current activity.
        """
        
        channel_data = turn_context.activity.channel_data if turn_context.activity.channel_data else {}
        treatment_group = channel_data.get("treatmentGroup", None)

        # If treatmentGroup is provided, store it. If not, do nothing here.
        if treatment_group is None:
            treatment_group = self.treatment_fallback
        else:
            try:
                treatment_group = int(treatment_group)
            except ValueError:
                treatment_group = self.treatment_fallback
        await self.treatment_state_accessor.set(turn_context, treatment_group)
        await self.conversation_state.save_changes(turn_context)

        return await super().on_conversation_update_activity(turn_context)
    
    async def on_members_added_activity(self, members_added: ChannelAccount, turn_context: TurnContext):
        """
        Initializes a new conversation. 
        - Sends the welcome message using the ConversationLogic class instance. 
        - Updates the conversation history. 
        - Switches the welcome_state variable. 

        Args: 
            members_added (ChannelAccount): The information about the user account. 
            turn_context (TurnContext): The information about the current activity.
        """

        # Retrieve welcome state
        welcome_sent = await self.welcome_state_accessor.get(turn_context, False)

        # Receive and specify treatment state
        treatment_group = await self.treatment_state_accessor.get(turn_context, self.treatment_fallback)

        # Generate initial welcome message
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id and not welcome_sent:
                conversation_history = await self.history_state_accessor.get(turn_context)
                if conversation_history is None:
                    conversation_history = []

                welcome_text = self.conversation_logic.get_welcome_message(
                    treatment_group,
                )
                conversation_history.append(("bot", welcome_text))
                await turn_context.send_activity(welcome_text)

                await self.history_state_accessor.set(turn_context, conversation_history)
                await self.welcome_state_accessor.set(turn_context, True)
                await self.conversation_state.save_changes(turn_context)

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Processes user messages.
        - Sends the bot response using the ConversationLogic class instance. 
        - Updates the conversation history. 
        
        Args:
            turn_context (TurnContext): The information about the current activity.
        """

        # Retrieve user message and send response
        treatment_group = await self.treatment_state_accessor.get(turn_context, self.treatment_fallback)
        user_text = turn_context.activity.text

        conversation_history = await self.history_state_accessor.get(turn_context)
        if conversation_history is None:
            conversation_history = []

        bot_response = self.conversation_logic.get_bot_message(
            treatment_group,
            conversation_history,
            user_text
        )

        conversation_history.append(("user", user_text))
        conversation_history.append(("bot", bot_response))
        await turn_context.send_activity(bot_response)

        await self.history_state_accessor.set(turn_context, conversation_history)
        await self.conversation_state.save_changes(turn_context)


class ConversationLogic:
    """
    Class that contains the logic for generating the bot's messages.
    """

    def __init__(self): 
        pass

    def get_welcome_message(self, treatment_group: int) -> str:
        """
        Returns the welcome message based on the treatment_group value. 

        Args: 
            treatment_group (int): The treatment group value. 

        Returns:
            str: The bot's welcome message. 
        """

        bot_welcome_message = ""

        if treatment_group == 1:
            bot_welcome_message = "Willkommen! Womit kann ich helfen?"

        else:
            bot_welcome_message = "Willkommen! Womit kann ich helfen?"

        return bot_welcome_message

    def get_bot_message(self, treatment_group: int, conversation_history: list, user_text: str) -> str:
        """
        Returns a bot response to a user message based on the treatment group value and the conversation history. 

        Args: 
            treatment_group (int): The treatment group value. 
            conversation_history (list): The previous messages of the conversation. 
            user_text (str): The current user message to be answered. 

        Returns:
            str: The bot's response to the user message.  
        """

        bot_message = ""

        if treatment_group == 1:
            bot_message = f"Danke für deine Nachricht. Du hast folgendes gesagt: '{user_text}'"
            
        else:
            bot_message = f"Du hast gesagt: '{user_text}'"

        return bot_message
