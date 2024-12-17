from botbuilder.core import ActivityHandler, TurnContext, ConversationState
from botbuilder.schema import ChannelAccount


class Bot(ActivityHandler):
    """
    Class that represents the chatbot.
    """

    def __init__(self, conversation_state: ConversationState):
        """
        Constructor of the Bot class. Specifies the state variables of a bot instance: 
        welcome_state: Specifies whether a bot instance is in the welcome state; 
        treatment_state: Specifies whether a bot instance should be treated as treatment or control group.

        Args: 
            conversation_state (ConversationState): The stored conversation state.
        """

        self.conversation_state = conversation_state
        self.welcome_state_accessor = self.conversation_state.create_property("WelcomeState")
        self.treatment_state_accessor = self.conversation_state.create_property("TreatmentGroup")
    
    async def on_members_added_activity(self, members_added: ChannelAccount, turn_context: TurnContext):
        """
        Initializes a new conversation. Sends the welcome message and switches the welcome_state variable. 
        Specifies the treatment_state variable.

        Args: 
            members_added (ChannelAccount): 
            turn_context (TurnContext): The information about the current activity.
        """

        # Retrieve welcome state
        welcome_sent = await self.welcome_state_accessor.get(turn_context, False)

        # Receive and specify treatment state
        channel_data = turn_context.activity.channel_data if turn_context.activity.channel_data else {}
        treatment_group = channel_data.get("treatment_group", None)
        if treatment_group is None:
            treatment_group = 1
        await self.treatment_state_accessor.set(turn_context, treatment_group)

        # Generate initial welcome message
        for member_added in members_added:
            if member_added.id != turn_context.activity.recipient.id and not welcome_sent:
                if treatment_group == 1:
                    await turn_context.send_activity("Willkommen! Womit kann ich helfen? (Treatment Chatbot)")
                else:
                    await turn_context.send_activity("Willkommen! Womit kann ich helfen? (Control Chatbot)")
                await self.welcome_state_accessor.set(turn_context, True)
                await self.conversation_state.save_changes(turn_context)

    async def on_message_activity(self, turn_context: TurnContext):
        """
        Processes user messages.
        
        Args:
            turn_context (TurnContext): The information about the current activity.
        """

        # Retrieve user message and send response
        treatment_group = await self.treatment_state_accessor.get(turn_context, 1)
        user_text = turn_context.activity.text
        if treatment_group == 1: 
            await turn_context.send_activity(f"Danke für deine Nachricht. Du hast folgendes gesagt: '{ user_text }'")
        else:
            await turn_context.send_activity(f"Du sagtest '{ user_text }'")

        # Save new conversation state
        await self.conversation_state.save_changes(turn_context)
