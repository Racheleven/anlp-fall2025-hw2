from sys import path_hooks
import json_repair
from langchain.agents import create_agent
from prompts.description_prompt import description_prompt
from prompts.reflection_prompt import reflection_prompt 
from prompts.voting_prompt import voting_prompt
import json
from agents.spy_cheatsheet_manager import SpyCheatSheetManager
class PlayerAgent:
    def __init__(self, model, pid, role=None, word=None,total_player_num=5,enable_cheatsheet=True,cheatsheet_prefix="default"):
        self.word=word
        self.role=role
        self.player_id = pid
        self.model=model
        self.agent=create_agent(  
            model,
            tools=[],
            system_prompt="You are a player in the SpyGame",
        )
        self.cheatsheet_prefix = cheatsheet_prefix
        self.log_info=[]
        self.memory=[]
        self.identity_info = [{"role": "unknown", "reason": "default value"}for _ in range(5)]
        self.enable_cheatsheet = enable_cheatsheet
        # Whether enable_cheatsheet = True or False,
        # always record these two fields for run_one_game() to use.
        self.model_api_key = "sk-amcjzxomyzuispivnvvtgszrnxijmxpkmewbvlviffgborlg"
        self.model_base_url = "https://api.siliconflow.cn/v1"

        # base_url fallback - this MUST not be None
        if self.model_base_url is None:
            self.model_base_url = "https://api.siliconflow.cn/v1"

        if enable_cheatsheet:
            self.cheatsheet = SpyCheatSheetManager(
                path=f"{self.cheatsheet_prefix}_cheatsheet_memory.json",
                api_key=self.model_api_key,
                base_url=self.model_base_url,
                prefix=self.cheatsheet_prefix
            )
        else:
            self.cheatsheet = None

    def add_memory(self,message):
        self.memory.append(message)

    def add_log_info(self,message):
        self.log_info.append(message)

    def ask(self,phase=None,round_num=None,alive_players_id=None,outlier_score=None):
        if phase=="description":
            print(f"Player {self.player_id} is describing his word in round {round_num}")
            prompt=self.get_description_prompt(round_num)
            response=self.invoke_model(prompt)
            response=json_repair.loads(response)
            self.add_log_info({"round_num":round_num,"role":self.player_id,"phase":"description","reason":response["thinking"],"content":response["content"]})
            return response["content"]
        
        if phase=="reflection":
            print(f"Player {self.player_id} is reflecting on his identity")
            prompt=self.get_reflection_prompt(round_num,alive_players_id,outlier_score)
            response=self.invoke_model(prompt)
            response=json_repair.loads(response)

            if "self_analysis" not in response or "player_analyses" not in response:
                raise ValueError("response must include self_analysis at top level")

            #update other players' identities
            for key,value in response["player_analyses"].items():
                if int(key)!=self.player_id and int(key) in alive_players_id:
                    role_guess=value["role_guess"]
                    word_guess=value["word_guess"]
                    reason=value["reason"]

                    self.identity_info[int(key)]={"role":role_guess,"word_guess":word_guess,"reason":reason}
                    self.add_log_info({"round_num":round_num,"role":self.player_id,"phase":"other_identity_guess","guess_player":key,"guess_role":role_guess,"guess_word":word_guess,"guess_reason":reason})

            #update self's identity
            sa = response["self_analysis"]
            role_guess = sa["role_guess"]
            reason = sa.get("role_reason", sa.get("reason", ""))
            confidence = sa["confidence"]
            outlier_used = sa.get("outlier_score_used", None)
            grounding_consistency = sa.get("grounding_consistency", "unknown")
            if role_guess not in ["spy", "civilian"]:
                if outlier_used is not None:
                    role_guess = "spy" if outlier_used >= 0.5 else "civilian"
                else:
                    role_guess = "civilian"
            
            self.identity_info[self.player_id] = {
                "role": role_guess,
                "reason": reason,
                "confidence": confidence,
                "outlier_score": outlier_used,
                "grounding_consistency": grounding_consistency
            }

            self.add_log_info({
                "round_num": round_num,
                "role": self.player_id,
                "phase": "self_identity_guess",
                "guess_role": role_guess,
                "guess_reason": reason,
                "confidence": confidence,
                "outlier_score": outlier_used,
                "grounding_consistency": grounding_consistency
            })
            return 

        if phase=="vote":
            print(f"Player {self.player_id} is voting")
            prompt=self.get_vote_prompt(round_num,alive_players_id)
            response=self.invoke_model(prompt)
            response=json_repair.loads(response)
            vote_target=response["vote_target"]
            vote_reason=response["vote_reason"]
            self.add_log_info({"round_num":round_num,"role":self.player_id,"phase":"vote","vote_target":vote_target,"vote_reason":vote_reason})
            return vote_target
        
        else:
            raise ValueError(f"Invalid phase: {phase}")
    
    def get_description_prompt(self,round_num):

        past_info_msg=self.create_past_info_msg()
        identity_info_msg=self.create_identity_info_msg()

        prompt=description_prompt.format(word=self.word,
                                        player_id=self.player_id,
                                        round_num=round_num,
                                        past_info=past_info_msg,
                                        identity_info=identity_info_msg,
                                        cheatsheet=self.get_cheatsheet_msg())
        return prompt

    def get_vote_prompt(self,round_num,alive_players_id):
        past_info_msg=self.create_past_info_msg()
        identity_info_msg=self.create_identity_info_msg()

        alive_players_msg=",".join([f"Player {player_id}" for player_id in alive_players_id if player_id != self.player_id])


        prompt=voting_prompt.format(word=self.word,
                                    player_id=self.player_id,
                                    round_num=round_num,
                                    past_info=past_info_msg,
                                    identity_info=identity_info_msg,
                                    alive_players=alive_players_msg,
                                    cheatsheet=self.get_cheatsheet_msg())

        #print("=================vote prompt==================")
        # print(prompt)
        return prompt
    
    def get_reflection_prompt(self,round_num,alive_players_id,outlier_score):
        past_info_msg=self.create_past_info_msg()
        # create identity_info_msg
        identity_info_msg=self.create_identity_info_msg()
        alive_players_msg=",".join([f"Player {player_id}" for player_id in alive_players_id])
        if outlier_score is None:
            grounding_signal = "OUTLIER SCORE not available for this round."
        else:
            grounding_signal = (
                f"Your OUTLIER SCORE = {outlier_score}.\n"
                "- 0.0 means you are VERY likely in the majority group.\n"
                "- 1.0 means you are VERY likely the odd one out (spy).\n"
                "If OUTLIER SCORE > 0.6, you should seriously consider you might be the spy.\n"
                "If OUTLIER SCORE < 0.3, you should seriously consider you might be a civilian.\n"
            )
        prompt=reflection_prompt.format(word=self.word,
                                        player_id=self.player_id,
                                        round_num=round_num,
                                        past_info=past_info_msg,
                                        alive_players=alive_players_msg,
                                        identity_info=identity_info_msg,
                                        cheatsheet=self.get_cheatsheet_msg(),
                                        grounding_signal=grounding_signal)

        return prompt

    def create_identity_info_msg(self):
        my_guess=self.identity_info[self.player_id]
        identity_info_msg=f"I am Player {self.player_id}. Up to this point, I think my role is [ {my_guess['role']} ],because [ {my_guess['reason']} ]. \n"
        for index,item in enumerate(self.identity_info):
            if item!=my_guess:
                identity_info_msg+=f"I think Player {index} is {item['role']}, because {item['reason']}.\n"
        return identity_info_msg
    

    def create_past_info_msg(self):
        msg=""
        for item in self.memory:
            if item['role']=='host':
                msg+=f"The Host said: {item['content']}\n"
            else:
                if item['phase']=='description':
                    msg+=f"Player {item['role']} said: {item['content']}\n"
                elif item['phase']=='vote':
                    msg+=f"Player {item['role']} voted for {item['content']}\n"
        # print(msg)
        return msg
    

    def invoke_model(self,prompt):
        inputs = {"messages": [{"role": "user", "content": prompt}]}
        response = self.agent.invoke(inputs)
        response = response['messages'][-1]
        # response = self.model.invoke(prompt)
        
        # print("=================response==================")
        print(response.content)
        return response.content
    
    def get_cheatsheet_msg(self):
        if not self.enable_cheatsheet or self.cheatsheet is None:
            return "(cheatsheet disabled)"
        return self.retrieve_memory()
    
    def retrieve_memory(self):
        if not self.enable_cheatsheet:
            return "(memory disabled)"
        query = f"word={self.word}, role={self.role}"
        topk = self.cheatsheet.retrieve(query, top_k=6)
        if not topk:
            return "(no relevant past memory)"
        return "\n".join([f"- {x}" for x in topk])
