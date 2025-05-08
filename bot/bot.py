from botbuilder.core import ActivityHandler, TurnContext, ConversationState
from botbuilder.schema import ChannelAccount, Activity, ActivityTypes

from bot.dialogue_start import DialogueStart
from bot.message_processing import MessageProcessing


class Bot(ActivityHandler):
    """
    Class that represents the chatbot.
    """

    def __init__(self, conversation_state: ConversationState, treatment_fallback: int):
        """
        Constructor of the Bot class. 
        - Specifies the conversation state variables of a bot instance: 
            - welcome_state_accessor: Specifies whether a bot instance is in the welcome state.
            - treatment_state_accessor: Specifies whether a bot instance should be treated as treatment or control group.
            - conversation_history_accessor: The conversation history. 
            - dialogue_state_history_accessor: The dialogue state history. 
            - slot_filling_accessor: The slot filling information. 
        - Initializes an instance of the StartDialogue class to initially start the dialogue.
        - Initializes an instance of the MessageProcessing class to process user messages. 
        
        Args: 
            conversation_state (ConversationState): The stored conversation state.
            treatment_fallback (int): Fallback value if no treatmentGroup provided in channel_data.
        """

        self.conversation_state = conversation_state
        self.treatment_fallback = treatment_fallback

        # Specify conversation state variables
        self.welcome_state_accessor = self.conversation_state.create_property("WelcomeState")
        self.treatment_state_accessor = self.conversation_state.create_property("TreatmentGroup")
        self.conversation_history_accessor = self.conversation_state.create_property("ConversationHistory")
        self.dialogue_state_history_accessor = self.conversation_state.create_property("DialogueStateHistory")
        self.slot_filling_accessor = self.conversation_state.create_property("SlotFilling")
        self.processed_messages_accessor = self.conversation_state.create_property("ProcessedMessages")

        self.dialogue_start = DialogueStart()
        self.message_processing = MessageProcessing()

    async def set_treatment_state(self, turn_context: TurnContext) -> int:
        """
        Retrieves the treatment group value from channel_data and stores it in the conversation state. 
        - Stores the treatmentGroup if provided in channel_data, otherwise uses the treatment_fallback value.

        Args: 
            turn_context (TurnContext): The information about the current activity.

        Returns: 
            int: The treatment_group value.
        """

        # Receive channel data
        channel_data = turn_context.activity.channel_data if turn_context.activity.channel_data else {}
        treatment_group = channel_data.get("treatmentGroup", None)

        # If no treatment_group value received: set treatment_group to fallback value
        if treatment_group is None: 
            treatment_group = self.treatment_fallback

        # If treatment_group value received: convert it to integer format and store it in the conversation state
        else:
            try:
                treatment_group = int(treatment_group)
            except ValueError: 
                treatment_group = self.treatment_fallback
            await self.treatment_state_accessor.set(turn_context, treatment_group)
            await self.conversation_state.save_changes(turn_context)
        
        return treatment_group
    
    async def get_treatment_state(self, turn_context: TurnContext) -> int:
        """
        Retrieves the treatment group value from the conversation state.
        - If there is no treatment group value stored in the conversation state, returns the treatment_fallback.
        
        Args: 
            turn_context (TurnContext): The information about the current activity.

        Returns: 
            int: The treatment_group value.
        """

        treatment_group = await self.treatment_state_accessor.get(turn_context, self.treatment_fallback)
        return treatment_group
    
    async def get_conversation_history(self, turn_context: TurnContext) -> list:
        """
        Retrieves the conversation history from the conversation state.
        - If there is no conversation history stored, returns an empty list.
        
        Args: 
            turn_context (TurnContext): The information about the current activity.

        Returns: 
            list: The conversation history.
        """

        conversation_history = await self.conversation_history_accessor.get(turn_context)
        if conversation_history is None:
            conversation_history = []
        
        return conversation_history
    
    async def get_dialogue_state_history(self, turn_context: TurnContext) -> list:
        """
        Retrieves the dialogue state history from the conversation state.
        - If there is no dialogue state history stored, returns an empty list.
        
        Args: 
            turn_context (TurnContext): The information about the current activity.

        Returns: 
            list: The dialogue state history.
        """

        dialogue_state_history = await self.dialogue_state_history_accessor.get(turn_context)
        if dialogue_state_history is None:
            dialogue_state_history = []

        return dialogue_state_history
    
    async def get_slot_filling(self, turn_context: TurnContext) -> dict:
        """
        Retrieves the slot filling dictionary from the conversation state.
        - If there is no slot filling dictionary stored, returns an empty dictionary.
        
        Args: 
            turn_context (TurnContext): The information about the current activity.

        Returns: 
            list: The slot filling dictionary.
        """

        slot_filling = await self.slot_filling_accessor.get(turn_context)
        if slot_filling is None:
            slot_filling = {}

        return slot_filling 
    
    async def is_duplicate_message(self, turn_context: TurnContext) -> bool:
        """
        Checks for an incoming message by the user, if this message has already been processed.
        - If the message has already been processed, returns True
        - If the message has not been processed, returns False

        Args: 
            turn_context (TurnContext): The information about the current activity.

        Returns:
            bool: Whether the message has already been processed. 
        """

        # Receive message key from channel data
        channel_data = turn_context.activity.channel_data if turn_context.activity.channel_data else {}
        message_key = channel_data.get("messageKey", None)

        # If no message_key value received: return False
        if message_key is None: 
            return False

        # If message_key is contained in the processed message_keys: return True
        processed_messages = await self.processed_messages_accessor.get(turn_context)
        if processed_messages is None:
            processed_messages = []
        if message_key in processed_messages:
            return True

        # If message_key is not contained in the processed message_keys: 
        # store the message_key in the conversation_state and return False
        processed_messages.append(message_key)
        await self.processed_messages_accessor.set(turn_context, processed_messages)
        return False
    
    async def on_members_added_activity(self, members_added: ChannelAccount, turn_context: TurnContext):
        """
        Initializes a new conversation. This function is executed when the user opens the chatbot. 
        - Retrieves the welcome_sent variable from the conversation state to check whether the welcome 
        message was already sent. 
        - Determines the treatment group value for the conversation and stores it in the conversation state. 
        - If the welcome message has not been sent to the user: Switches the welcome_sent variable, sends 
        the welcome message, initializes the conversation history and dialogue state history and updates the 
        conversation state. 

        Args: 
            members_added (ChannelAccount): The information about the user account. 
            turn_context (TurnContext): The information about the current activity.
        """

        # Retrieve welcome state 
        welcome_sent = await self.welcome_state_accessor.get(turn_context, False)

        # Retrieve treatment_group value and set conversation state accordingly
        await self.set_treatment_state(turn_context)

        # Generate initial welcome message and initialize dialogue state variables
        # the first time a user enters the chat. 
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id and not welcome_sent:

                # Retrieve conversation state variables
                conversation_history = await self.get_conversation_history(turn_context)
                dialogue_state_history = await self.get_dialogue_state_history(turn_context)
                
                # Retrieve welcome text and initial state
                welcome_text, initial_dialogue_state = self.dialogue_start.start_dialogue()

                # Update the conversation state variables
                conversation_history.append(("bot", welcome_text))
                dialogue_state_history.append(initial_dialogue_state)

                # Send welcome message
                activity = Activity(
                    type=ActivityTypes.message,
                    text=welcome_text,
                    channel_data={"dialogueState": initial_dialogue_state}
                )
                await turn_context.send_activity(activity)
                
                # Store updated conversation state variables
                await self.conversation_history_accessor.set(turn_context, conversation_history)
                await self.dialogue_state_history_accessor.set(turn_context, dialogue_state_history)
                await self.welcome_state_accessor.set(turn_context, True)
                await self.conversation_state.save_changes(turn_context)

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Processes a user message. This function is executed each time the user 
        sends a message to the chatbot. 
        - Retrieves the conversation state variables of the conversation.
        - Checks whether the message is a duplicate. 
        - Receives the user message.
        - Executes the process_message function from the MessageProcessing 
        class to determine the bot response, the new dialogue state, the 
        final_state flag and the new slot filling dictionary, given the user 
        message, the treatment group value, the conversation history, the 
        dialogue state history and the current slot filling dictionary. 
        - Sends the bot response and the final_state metadata.
        - Updates the conversation state.  
        
        Args:
            turn_context (TurnContext): The information about the current 
            activity.
        """

        # Check if the message is a duplicate; if this is the case, stop the function
        if await self.is_duplicate_message(turn_context):
            return

        # Retrieve conversation state variables
        treatment_group = await self.get_treatment_state(turn_context)
        conversation_history = await self.get_conversation_history(turn_context)
        dialogue_state_history = await self.get_dialogue_state_history(turn_context)
        slot_filling = await self.get_slot_filling(turn_context)

        # Extract the user message
        user_text = turn_context.activity.text

        # Process the user message
        bot_response, new_dialogue_state, final_state, new_slot_filling = self.message_processing.process_message(
            user_text,
            treatment_group,
            conversation_history,
            dialogue_state_history,
            slot_filling
        )

        # Update the conversation state variables
        conversation_history.append(("user", user_text))
        conversation_history.append(("bot", bot_response))
        dialogue_state_history.append(new_dialogue_state)
        slot_filling = new_slot_filling

        # Send an activity object with the bot response and the final_state 
        # value as metadata
        activity = Activity(
            type=ActivityTypes.message,
            text=bot_response,
            channel_data={"finalState": final_state, "dialogueState": new_dialogue_state}
        )
        await turn_context.send_activity(activity)
        print(f"User message: {user_text}\nChatbot response: {bot_response}\nNew State: {new_dialogue_state}\n\n\n")

        # Store updated conversation state variables
        await self.conversation_history_accessor.set(turn_context, conversation_history)
        await self.dialogue_state_history_accessor.set(turn_context, dialogue_state_history)
        await self.slot_filling_accessor.set(turn_context, slot_filling)
        await self.conversation_state.save_changes(turn_context)       
