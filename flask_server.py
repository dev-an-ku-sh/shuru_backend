from flask import Flask, request, jsonify
from flask_cors import CORS
import autogen
import ast


#Local LLM Config
mistral = {
    "config_list": [
        {
            "model": "TheBloke/Mistral-7B-Instruct-v0.2-GGUF",
            "base_url": "http://localhost:1234/v1",
            "api_key": "lm-studio"
        }
    ],
    "cache_seed": None,
    "max_tokens": 1024,
    "temperature": 1,  #lower = less creative. [0,1]
    "timeout": 240,
}

#User Proxy Agent
user_proxy = autogen.UserProxyAgent(
    name="Pseudo Admin",
    # default_auto_reply="No need for further improvement, the refactored version is good enough",  # needed for local LLMs
    default_auto_reply= "...",
    code_execution_config={
        "work_dir": "code",
        "use_docker": False
    },
    human_input_mode="NEVER",
)

app = Flask(__name__)
# Apply CORS to all routes, Needed for POST from Website
CORS(app)

#Rephrase()
@app.route('/rephrase', methods=['POST'])
def rephrase():
    
    #Re-phrasing assistant
    rephrasing_assistant = autogen.AssistantAgent(
        name="Assistant",
        llm_config=mistral,
        system_message='''You are an assistant that re-phrases the statement 
        so that it makes sense and write it as a question, you do not have to provide a solution.''',
    )
    
    #Rephrasing Chat
    msg = request.json.get('problem_statement')
    message = f'''Please re-phrase the following statement so that it makes sense and write it as a question: '{msg}',
    provide only one sentence as the response, DO NOT provide a solution.'''
    chat_result = user_proxy.initiate_chat(recipient=rephrasing_assistant, message=message, silent=False, max_turns=1)
    return jsonify({"response": chat_result.chat_history[1]['content']})


#Rephrase_With_Feedback
@app.route('/rephrase_with_feedback', methods=['POST'])
def rephrase_with_feedback():
    
    #Re-phrasing assistant
    rephrasing_assistant = autogen.AssistantAgent(
        name="Assistant",
        llm_config=mistral,
        system_message="You are an assistant that re-phrases the statement so that it makes sense and write it as a question, you do not have to provide a solution.",
    )

    #Rephrasing with Feedback Chat
    previous_ver = request.json.get('previous_ver')
    feedback = request.json.get('feedback')
    if previous_ver is None or feedback is None:
        return jsonify({"error": "Both previous_ver and feedback must be provided"}), 400
    message = f'''Please re-phrase the following statement so that it makes sense and write it as a question: '{previous_ver}', based on the feedback: '{feedback}',
    provide only one sentence as the response, DO NOT provide a solution.'''
    chat_result = user_proxy.initiate_chat(recipient=rephrasing_assistant, message=message, silent=False, max_turns=1)
    return jsonify({"response": chat_result.chat_history[1]['content']})

#Persona Creation
@app.route('/create_persona_list', methods=['POST'])
def create_persona_list():
    
    #Persona_Creator Assistant
    persona_creator_assistant = autogen.AssistantAgent(
        name="Persona Creator Assistant",
        llm_config=mistral,
        system_message="Refer to this example list: [['Population Control Paul', 'Promote and implement government policies that provide incentives for smaller families such as financial benefits and subsidies.'],['Educated Eva', 'Advocate for and invest in accessible education for girls and women to increase their economic opportunities, leading to later marriage and fewer children.'],['Sustainability Sam', 'Encourage sustainable living practices and access to family planning resources to help individuals make informed decisions about the number of children they want.'],['Religious Reuben', 'Collaborate with religious leaders and institutions to promote responsible family planning within their communities, incorporating teachings that emphasize the importance of small families.'],['Technology Tamara', 'Leverage technology such as education apps, contraceptive delivery services, and telemedicine to make family planning more accessible and convenient.']], you have to create a list of 5 imaginary personas having unique and contradicting opinions on how approach the solution of the given problem. The list should follow the exact format of the example list mentioned before. Do not output anything else except the list. Only the list is needed"
     )
    problem_statement = request.json.get("problem_statement")
    if problem_statement is None:
        return jsonify({"error": "Problem statement must be provided"}), 400

    chat_result = user_proxy.initiate_chat(recipient=persona_creator_assistant, 
                                           message=problem_statement, silent=False, max_turns=1)
    raw_list = chat_result.chat_history[1]['content']
    print(raw_list)

    # Find the start and end of the list in the string
    start_index = raw_list.find('[')
    end_index = raw_list.rfind(']') + 1  # +1 to include the closing bracket

    # Extract the list part of the string if both '[' and ']' are found
    if start_index != -1 and end_index != -1:
        list_str = raw_list[start_index:end_index]
    else:
        return jsonify({"error": "List not found in response"}), 400

    # Use ast.literal_eval to safely evaluate the string representation of the list
    try:
        evaluated_list = ast.literal_eval(list_str)
    except (ValueError, SyntaxError):
        # Handle the error if list_str is not a valid Python literal
        return jsonify({"error": "Invalid list format"}), 400

    # Return the evaluated list directly in the response
    return jsonify({"response": evaluated_list})

#get agent perspectives
@app.route('/get_agent_perspective', methods=['POST'])
def get_agent_perspective():
    agent_name = request.json.get("agent_name"), 
    agent_perspective = request.json.get("agent_perspective"), 
    problem_statement = request.json.get("problem_statement")
    assistant = autogen.AssistantAgent(
        name = agent_name, 
        system_message= f"You are {agent_name}, your perspective is : {agent_perspective}",
        llm_config=mistral,
        max_consecutive_auto_reply=1
    )
    chat_result = user_proxy.initiate_chat(recipient=assistant, message= f'based on the perspective defined in your system message, find a solution to {problem_statement} in 20 words', silent = False, max_turns=1)
    return jsonify({"response": chat_result.chat_history[1]['content']})

#get agent feedbacks
@app.route('/get_agent_feedback', methods=['POST'])
def get_agent_feedback():
    agent_name = request.json.get("agent_name"), 
    agent_perspective = request.json.get("agent_perspective"), 
    problem_statement = request.json.get("problem_statement")
    solution = request.json.get("solution")
    para_pov = "";
    assistant = autogen.AssistantAgent(
        name = agent_name, 
        system_message= f"You are {agent_name}, your perspective is : {agent_perspective}",
        llm_config=mistral,
        max_consecutive_auto_reply=1
    )
    chat_result = user_proxy.initiate_chat(recipient=assistant, message= f'The solution : {solution} is being proposed for the problem {problem_statement}, based on the perspective defined in your system message, provide criticism and suggest improvements in 20 words on the proposed solution', silent = False, max_turns=1)
    return jsonify({"response": chat_result.chat_history[1]['content']})

#get agent perspectives
@app.route('/get_agent_perspectives', methods=['POST'])
def get_agent_perspectives():
    para_pov = "";
    agent_list_str = request.json.get("agent_list")
    agent_list = ast.literal_eval(agent_list_str)
    problem_statement = request.json.get("problem_statement")
    for agent in agent_list:
        assistant = autogen.AssistantAgent(
            name = agent[0], 
            system_message= f"You are {agent[0]}, your perspective is : {agent[1]}",
            llm_config=mistral,
            max_consecutive_auto_reply=1
        )
        chat_result = user_proxy.initiate_chat(recipient=assistant, message= f'based on the perspective defined in your system message, find a solution to {problem_statement} in 20 words', silent = False, max_turns=1)
        para_pov = para_pov + chat_result.chat_history[1]['content'];
    print(para_pov)
    return jsonify({"response": para_pov})

#get agent feedbacks
@app.route('/get_agent_feedbacks', methods=['POST'])
def get_agent_feedbacks():
    agent_list_str = request.json.get("agent_list")
    agent_list = ast.literal_eval(agent_list_str)
    problem_statement = request.json.get("problem_statement")
    solution = request.json.get("solution")
    para_pov = "";
    for agent in agent_list:
        assistant = autogen.AssistantAgent(
            name = agent[0], 
            system_message= f"You are {agent[0]}, your perspective is : {agent[1]}",
            llm_config=mistral,
            max_consecutive_auto_reply=1
        )
        chat_result = user_proxy.initiate_chat(recipient=assistant, message= f'The solution : {solution} is being proposed for the problem {problem_statement}, based on the perspective defined in your system message, provide criticism and suggest improvements in 20 words on the proposed solution', silent = False, max_turns=1)
        para_pov = para_pov + chat_result.chat_history[1]['content'];
    print(para_pov)
    return jsonify({"response": para_pov})

#generate_solution
@app.route('/generate_solution', methods=['POST'])
def generate_solution():
    
    #Ideation assistant
    ideation_assistant = autogen.AssistantAgent(
        name="Assistant",
        llm_config=mistral,
        system_message="You are an assistant that carefully analysises the list of perspectives given on a problem statement and suggests a solution",
    )

    #Ideation chat
    pov_para = request.json.get('pov_para')
    problem_statement = request.json.get('problem_statement')
    if pov_para is None or problem_statement is None:
        return jsonify({"error": "Both povs & ps must be provided"}), 400
    message = f'''Based on the perspectives described here: {pov_para}, form a step wise solution on the problem statement: {problem_statement} in 120 words'''
    chat_result = user_proxy.initiate_chat(recipient=ideation_assistant, message=message, silent=False, max_turns=1)
    return jsonify({"response": chat_result.chat_history[1]['content']})

#generate_solution_with_feedback
@app.route('/generate_solution_with_feedback', methods=['POST'])
def generate_solution_with_feedback():
    
    #Ideation assistant
    ideation_assistant = autogen.AssistantAgent(
        name="Assistant",
        llm_config=mistral,
        system_message="You are an assistant that carefully analysises the list of perspectives given on a problem statement and suggests a solution",
    )

    #Ideation chat
    feedback = request.json.get('feedback')
    prev_solution = request.json.get('prev_solution')
    problem_statement = request.json.get('problem_statement')
    if feedback is None or problem_statement is None:
        return jsonify({"error": "Both povs & ps must be provided"}), 400
    message = f'''Based on the criticism and suggestions described here: {feedback}, improvise the solution : {prev_solution} for solving the problem statement: {problem_statement} in 120 words'''
    chat_result = user_proxy.initiate_chat(recipient=ideation_assistant, message=message, silent=False, max_turns=1)
    return jsonify({"response": chat_result.chat_history[1]['content']})


if __name__ == "__main__":
    app.run(debug=True)