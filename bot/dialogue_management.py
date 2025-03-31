import json
import os


class DialogueManagement:
    """
    Class that performs the dialogue management.
    """

    def __init__(self, state_info: dict, edge_conditions: dict, final_state: str):
        """
        Constructor of the DialogueManagement class.
        - Initializes the state_info dictionary and the edge_conditions 
        dictionary. 

        Args:
            state_info (dict): The dictionary with the state information. 
            edge_conditions (dict): The dictionary with the edge conditions.
            final_state (str): The final state.
        """

        self.state_info = state_info
        self.edge_conditions = edge_conditions
        self.final_state = final_state

    def run(self, current_dialogue_state: str, slot_filling: dict, newly_filled_slots: dict) -> tuple[str, str, bool]:
        """
        Performs the dialogue management.
        - Determines the relevant edge for the current dialogue state given the 
        newly filled slots.
        - Determines the new state and the action based on the dialogue state 
        graph and the edge conditions graph.
        - Checks whether the new state equals the final state.
        
        Args: 
            current_dialogue_state (str): The current dialogue state.
            slot_filling (dict): The slot filling dictionary.
            newly_filled_slots (dict): The newly filled slots by the last user 
            message. 

        Returns: 
            tuple[str, str, bool]: A tuple with the new dialogue state, the 
            action and a flag whether the new dialogue state equals the final 
            state. 
        """

        # Determine the relevant edge for the current dialogue state given the 
        # newly filled slots
        edge = self._determine_edge(current_dialogue_state, newly_filled_slots)

        # Determine the new state and the action based on the dialogue state 
        # graph and the edge conditions graph
        new_state, rg_action = self._get_new_state_and_action(current_dialogue_state, 
                                                           edge, 
                                                           slot_filling)

        # Check whether the new state equals the final state
        final_state = self._final_state_check(new_state)

        return new_state, rg_action, final_state
    
    def _determine_edge(self, current_dialogue_state: str, newly_filled_slots: dict) -> str:
        """
        Determines the relevant edge on the state graph.
        - The choide is based on the current dialogue state and the newly filled 
        slots given the state and edge information in the self.state_info
        dictionary.
        
        Args:
            urrent_dialogue_state (str): The current dialogue state.
            newly_filled_slots (dict): The newly filled slots by the last user 
            message. 
        
        Returns:
            str: The relevant edge in the state graph.
        """
        
        # Create a set containing only the newly filled slots which are 
        # relevant for the transition
        newly_filled_slot_set = {slot for slot, value in 
                                 newly_filled_slots.items() if value == 1}
        slots_for_transition = set(self.state_info[current_dialogue_state]
                                   ["slots_for_transition"])
        filled_transition_slots = newly_filled_slot_set & slots_for_transition
        
        # Return the edge which contains the slot combination from 
        # newly_filled_slots
        edges = self.state_info[current_dialogue_state]["edges"]
        for edge, slot_combis in edges.items():
            slot_combis = [set(slot_combi) for slot_combi in slot_combis]
            if filled_transition_slots in slot_combis:
                return edge
        
        # Fallback: Return the fallback next edge of the current dialogue state
        return self.state_info[current_dialogue_state]["fallback_next_edge"]
    
    def _get_new_state_and_action(self, current_dialogue_state: str, edge: str, slot_filling: dict) -> tuple[str, str]:
        """
        Determines the new state and the action based on the relevant edge.
        - Traces the edge conditions in self.state_info and self.edge_conditions
        considering the current slot_filling dictionary to extract the next 
        state and the relevant action.
        
        Args:
            current_dialogue_state (str): The current dialogue state.
            edge (str): The relevant edge in the state graph.
            slot_filling (str): The slot filling dictionary.
        
        Returns:
            tuple[str, str]: The new state and the action.
        """

        # Retrieve the relevant edge policy
        edge_policies = self.state_info[current_dialogue_state].get(
            "edge_policy", {})
        edge_policy = edge_policies[edge]

        # If there is no edge condition, directly extract the new state and the 
        # rg_action
        if edge_policy["type"] == "direct":
            new_state = edge_policy["next_state"]
            rg_action = edge_policy["rg_action"]

        # If there is an edge condition, call the 
        # self._trace_edge_conditions(condition) function to check the edge 
        # conditions and get the relevant new state and rg_action
        else:
            condition = edge_policy["condition"]
            new_state, rg_action = self._trace_edge_conditions(condition, 
                                                               slot_filling)
        
        # Translate the new dialogue state into a correct format
        new_state = self._format_new_state(new_state, current_dialogue_state)
        
        return new_state, rg_action
    
    def _trace_edge_conditions(self, condition: str, slot_filling: dict) -> tuple[str, str]:
        """
        Recursively traces the edge conditions.
        - Checks whether the current slot_filling fulfills the condition.
        - Recursively calls itself until a next state and an rg_action is found.
        
        Args:
            condition (str): The name of the condition to check.
            slot_filling (dict): The slot filling dictionary.
        
        Returns:
            tuple[str, str]: The new state and the action.
        """

        # Retrieve the relevant edge condition info
        condition_info = self.edge_conditions[condition]

        # Check whether the conditional slot is fulfilled and move to the 
        # respective branch
        conditional_slot = condition_info["conditional_slot"]
        branch = "if_true" if slot_filling.get(
            conditional_slot) == 1 else "if_false"
        branch_policy = condition_info[branch]
        
        # If there is no further edge condition in the respective branch, 
        # directly extract the new state and the rg_action
        if branch_policy["type"] == "direct":
            new_state = branch_policy["next_state"]
            rg_action = branch_policy["rg_action"]
        
        # If there is a further edge condition in the respective branch, 
        # recursively call the _trace_edge_conditions function
        else:
            next_condition = branch_policy["condition"]
            new_state, rg_action = self._trace_edge_conditions(next_condition, 
                                                               slot_filling)
        
        return new_state, rg_action
    
    def _format_new_state(self, new_state: str, current_dialogue_state: str) -> str:
        """
        Translates the new dialogue state into a correct format.
        Catches special next_state strings.
        - Catches the case where next_state = 'current_state' and replaces the 
        new state by the actual current state.
        
        Args:
            new_state (str): The determined new_state string in a raw format.
            current_dialogue_state (str): The current dialogue state.
        
        Returns:
            str: The actual new state in a correct format.
        """

        if new_state == "current_state":
            new_state = current_dialogue_state
        return new_state
    
    def _final_state_check(self, new_state: str) -> bool:
        """
        Checks whether the new state equals the final state.
        - if this is the case, returns True, otherwise returns Fals.

        Args:
            new_state (str): The new state determined by the dialogue 
            management.
        
        Returns:
            bool: A flag indicating whether the final state has been reached.
        """

        return new_state == self.final_state
    
    def run_fallback(self, current_dialogue_state: str) -> tuple[str, str, bool]:
        """
        Fallback dialogue management function.
        - This function is called if an exception occurred during the execution 
        of the run function.
        - Simply uses the current dialogue state to return the fallback next 
        state and the fallback rg_action specified in the states.json file.
        - Checks whether the new state equals the final state.
        
        Args: 
            current_dialogue_state (str): The current dialogue state.

        Returns: 
            tuple[str, str, bool]: A tuple with the new dialogue state, the 
            action and a flag whether the new dialogue state equals the final 
            state. 
        """

        new_state = self.state_info[current_dialogue_state][
            "fallback_next_state"]
        rg_action = self.state_info[current_dialogue_state][
            "fallback_rg_action"]
        final_state = self._final_state_check(new_state)

        return new_state, rg_action, final_state
