from itertools import chain, combinations

from bot.bot import Bot
from bot.message_processing import MessageProcessing
from bot.slot_filling import SlotFilling
from bot.dialogue_management import DialogueManagement
from bot.response_generation import ResponseGeneration

# Create class instances
message_processing_inst = MessageProcessing()
slot_filling_inst = SlotFilling(message_processing_inst.slot_template, message_processing_inst.state_info)
dialogue_management_inst = DialogueManagement(message_processing_inst.state_info, 
                                         message_processing_inst.edge_conditions, 
                                         message_processing_inst.final_state)
response_generation_inst = ResponseGeneration(message_processing_inst.rg_mapping)

def run_test():
    """
    Function to secify the test to run.
    """

    #get_slot_filling_prompts_test()
    #run_slot_filling_test()
    #run_dialogue_management_test()
    bulk_run_dialogue_management_test()
    #run_get_conv_history_for_prompt_test()
    #run_get_rg_dev_prompt_test()
    #run_get_rg_user_prompt_test()
    #run_response_generation_test()
    #bulk_run_response_generation_test()
    #run_dialogue_management_fallback_test()
    #run_slot_filling_fallback_test()
    #run_response_generation_fallback_test()


def get_slot_filling_prompts_test():
    developer_prompt, user_prompt = slot_filling_inst._get_slot_filling_prompts("test bot message", "test user message", ["a", "b", "c", "c_val", "d", "d_val", "e", "f"])
    print(developer_prompt)
    print("")
    print("")
    print(user_prompt)

def run_slot_filling_test():
    user_text_1 = "Ich habe eine Bestellung bei euch gemacht, aber es ist nicht alles angekommen."
    user_text_2 = "Ich habe eine Bestellung bei euch gemacht, aber die Uhr ist nicht angekommen."
    user_text_3 = "Ich habe eine Bestellung bei euch gemacht, aber der Pulllover ist nicht angekommen."
    current_dialogue_state = "0"
    conversation_history = [("bot", "Willkommen bei Salando! Ich bin Bob, ihr virtueller Assistent. Womit kann ich Ihnen helfen?")]
    newly_filled_slots = slot_filling_inst.run(
        user_text=user_text_2,
        current_dialogue_state=current_dialogue_state,
        conversation_history=conversation_history
    )
    print(newly_filled_slots)

def run_dialogue_management_test():
    current_dialogue_state = "0"
    slot_filling = {
        "a": 1, 
        "b": 1, 
        "c": 1,
        "c_val": 1,
        "d": 1,
        "d_val": 1,
        "e": 1,
    }
    newly_filled_slots = {
        "a": 1, 
        "b": 1, 
        "c": 1,
        "c_val": 1,
        "d": 1,
        "d_val": 1,
    }
    new_state, action, final_state = dialogue_management_inst.run(
        current_dialogue_state=current_dialogue_state,
        slot_filling=slot_filling,
        newly_filled_slots=newly_filled_slots
    )
    print(f"New State: {new_state}")
    print(f"Action: {action}")
    print(f"Final State: {final_state}")

def powerset(iterable):
        s = list(iterable)
        return chain.from_iterable(combinations(s, r) for r in range(len(s) + 1))

def bulk_run_dialogue_management_test():
    dialogue_states = ["0", "A", "D", "AB", "AD", "C", "BD", "CD", "F", "G", "H"]
    slots = ["a", "b", "c", "c_val", "d", "d_val", "f", "g", "h"]
    current_dialogue_state = "0"
    for combination in powerset(slots):
        for current_dialogue_state in dialogue_states:
            filled_slots = {key: 1 for key in combination}
            print(f"Current State: {current_dialogue_state}")
            print(filled_slots)
            new_state, action, final_state = dialogue_management_inst.run(
                current_dialogue_state=current_dialogue_state,
                slot_filling=filled_slots,
                newly_filled_slots=filled_slots
            )
            print(f"New State: {new_state}")
            print(f"Action: {action}")
            print(f"Final State: {final_state}")
            print("")

def run_get_conv_history_for_prompt_test(intermediate=0):
    user_text = "Letze Nachricht des Nutzers"
    conversation_history = [("bot", "Wilkommen ..."), ("user", "Hi ..."), ("bot", "Können Sie bitte genauer das Problem beschreiben?"), ("user", "Klar, ..."), ("bot", "Okay ...")]
    lastx = 4
    conv_hist_for_prompt = response_generation_inst._get_conv_hist_for_prompt(
        conversation_history=conversation_history,
        user_text=user_text,
        lastx=lastx
    )
    if intermediate == 0:
        print(conv_hist_for_prompt)
    else:
        return conv_hist_for_prompt

def run_get_rg_dev_prompt_test():
    treatment_group = 1
    action = "A_repeat"
    rg_dev_prompt = response_generation_inst._get_rg_dev_prompt(action, treatment_group)
    print(rg_dev_prompt)

def run_get_rg_user_prompt_test():
    treatment_group = 1
    action = "CD_wrong_article_forward_pass_e"
    conv_hist_for_prompt = run_get_conv_history_for_prompt_test(intermediate=1)
    rg_user_prompt = response_generation_inst._get_rg_user_prompt(action, treatment_group, conv_hist_for_prompt)
    print(rg_user_prompt)

def run_response_generation_test():
    treatment_group = 1
    conversation_history = [
        ("bot", "Willkommen bei Salando! Ich bin Bob, ihr virtueller Assistent. Womit kann ich Ihnen helfen?"),
        ("user", "Ich habe eine Armbanduhr bei euch bestellt, aber sie ist nicht angekommen."),
        ("bot", "Das tut mir leid zu hören. Ich kann verstehen, dass das ärgerlich ist. Können Sie mir bitte Ihre Bestellnummer mitteilen, damit ich Ihre Bestellung in unserem Sysstem einsehen kann?")
    ]
    user_text = "Ja, meine Bestellnummer ist 224466."
    rg_action = "CD_standard"
    bot_response = response_generation_inst.run(
        user_text=user_text,
        rg_action=rg_action,
        treatment_group=treatment_group,
        conversation_history=conversation_history,
    )
    print(bot_response)

def bulk_run_response_generation_test():
    treatment_group = 1
    conversation_history = [
        ("bot", "Willkommen bei Salando! Ich bin Bob, ihr virtueller Assistent. Womit kann ich Ihnen helfen?"),
        ("user", "Ich habe eine Armbanduhr bei euch bestellt, aber sie ist nicht angekommen."),
        ("bot", "Das tut mir leid zu hören. Ich kann verstehen, dass das ärgerlich ist. Können Sie mir bitte Ihre Bestellnummer mitteilen, damit ich Ihre Bestellung in unserem Sysstem einsehen kann?")
    ]
    user_text = "Ja, meine Bestellnummer ist 224466."
    rg_actions = ["0_repeat", "A_repeat", "A_standard", "AB_repeat", "AB_standard", "AD_repeat", "AD_standard", "AD_wrong_number", 
                  "BD_forward_pass_e", "BD_forward_pass_f", "BD_repeat", "BD_standard", "BD_wrong_number", "C_repeat", "C_standard", 
                  "CD_forward_pass_e", "CD_forward_pass_f", "CD_repeat", "CD_standard", "CD_wrong_article_forward_pass_e", 
                  "CD_wrong_article_forward_pass_f", "CD_wrong_article_standard", "CD_wrong_number", "D_repeat", "D_standard", 
                  "D_wrong_number", "E_standard", "F_standard", "G_final", "G_standard", "H_standard"]
    for rg_action in rg_actions:
        bot_response = response_generation_inst.run(
            user_text=user_text,
            rg_action=rg_action,
            treatment_group=treatment_group,
            conversation_history=conversation_history,
        )
        print(bot_response)

def run_dialogue_management_fallback_test():
    states = ["0", "A", "D", "AB", "AD", "C", "BD", "CD", "E", "F", "G", "H"]
    for current_dialogue_state in states: 
        new_state, action, final_state = dialogue_management_inst.run_fallback(
            current_dialogue_state=current_dialogue_state
        )
        print(f"New State: {new_state}")
        print(f"Action: {action}")
        print(f"Final State: {final_state}")

def run_slot_filling_fallback_test():
    user_text_1 = "Ich habe eine Bestellung bei euch gemacht, aber es ist nicht alles angekommen."
    user_text_2 = "Der Pullover ist nicht geliefert worden. Meine Bestellnummer ist 2246. Könnt Ihr mir den Preis bitte erstatten?"
    user_text_3 = "Meine Bestellung ist nicht angekommen."
    user_text_4 = "Der bestellte Pullover ist nicht angekommen."
    user_text_5 = "Ich habe bei euch einen Pullover und eine Hose bestellt. Allerdings hat der Pulli im Paket gefehlt. Was kann ich machen?"
    user_text_6 = "Es fehlt der Pullover in der Lieferung, während die Hose angekommen ist."
    current_dialogue_state = "0"
    newly_filled_slots = slot_filling_inst.run_fallback(
        user_text=user_text_6,
        current_dialogue_state=current_dialogue_state
    )
    print(newly_filled_slots)

def run_response_generation_fallback_test():
    rg_action = "BD_wrong_number"
    treatment_group = 0
    canned_response = response_generation_inst.run_fallback(rg_action, treatment_group)
    print(canned_response)


if __name__ == "__main__":
    run_test()
