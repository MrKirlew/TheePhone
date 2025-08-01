# perception_engine.py - Advanced Perception and Context Awareness Module
import re
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import hashlib

logger = logging.getLogger(__name__)

class PerceptionEngine:
    """Advanced perception system for understanding context, environment, and user state"""
    
    def __init__(self):
        self.environmental_context = {
            "time_of_day": None,
            "day_of_week": None,
            "season": None,
            "location": None,
            "weather": None,
            "device_type": None,
            "interaction_mode": None  # voice, text, multimodal
        }
        
        self.user_state = {
            "emotional_state": "neutral",
            "energy_level": "normal",
            "stress_level": "low",
            "engagement_level": "medium",
            "urgency": "normal",
            "mood_trajectory": []  # Track mood changes over time
        }
        
        self.conversational_context = {
            "topic_depth": 0,  # How deep into a topic
            "topic_switches": 0,  # How many topic changes
            "question_types": [],  # Types of questions asked
            "interaction_pattern": "exploratory",  # exploratory, task-focused, social
            "conversation_flow": "normal"  # normal, rapid, slow
        }
        
        self.behavioral_patterns = {
            "interaction_times": [],
            "common_topics": {},
            "communication_preferences": {
                "verbosity": "medium",
                "formality": "balanced",
                "detail_level": "moderate"
            },
            "response_preferences": {
                "prefers_examples": False,
                "prefers_step_by_step": False,
                "prefers_summaries": False
            }
        }
        
    def perceive_environment(self, metadata: Dict) -> Dict:
        """Analyze environmental context from metadata"""
        current_time = datetime.utcnow()
        
        # Time perception
        hour = current_time.hour
        if 5 <= hour < 12:
            self.environmental_context["time_of_day"] = "morning"
        elif 12 <= hour < 17:
            self.environmental_context["time_of_day"] = "afternoon"
        elif 17 <= hour < 21:
            self.environmental_context["time_of_day"] = "evening"
        else:
            self.environmental_context["time_of_day"] = "night"
            
        # Day perception
        self.environmental_context["day_of_week"] = current_time.strftime("%A")
        is_weekend = current_time.weekday() >= 5
        
        # Season perception (Northern Hemisphere)
        month = current_time.month
        if month in [12, 1, 2]:
            self.environmental_context["season"] = "winter"
        elif month in [3, 4, 5]:
            self.environmental_context["season"] = "spring"
        elif month in [6, 7, 8]:
            self.environmental_context["season"] = "summer"
        else:
            self.environmental_context["season"] = "fall"
            
        # Device and interaction mode
        if metadata.get("has_audio"):
            self.environmental_context["interaction_mode"] = "voice"
        elif metadata.get("has_image"):
            self.environmental_context["interaction_mode"] = "multimodal"
        else:
            self.environmental_context["interaction_mode"] = "text"
            
        return {
            "environment": self.environmental_context,
            "is_weekend": is_weekend,
            "is_business_hours": 9 <= hour < 17 and not is_weekend
        }
        
    def perceive_user_state(self, text: str, conversation_history: List[Dict]) -> Dict:
        """Analyze user's emotional and mental state"""
        
        # Emotional state detection
        emotional_state = self._detect_emotion(text)
        self.user_state["emotional_state"] = emotional_state
        
        # Energy level detection
        energy_level = self._detect_energy_level(text)
        self.user_state["energy_level"] = energy_level
        
        # Stress level detection
        stress_indicators = ["stressed", "overwhelmed", "too much", "can't handle", "frustrated", 
                           "deadline", "pressure", "urgent", "asap", "immediately"]
        stress_count = sum(1 for indicator in stress_indicators if indicator in text.lower())
        if stress_count >= 2:
            self.user_state["stress_level"] = "high"
        elif stress_count == 1:
            self.user_state["stress_level"] = "medium"
        else:
            self.user_state["stress_level"] = "low"
            
        # Urgency detection
        urgency_indicators = ["urgent", "asap", "immediately", "right now", "quickly", "hurry"]
        if any(indicator in text.lower() for indicator in urgency_indicators):
            self.user_state["urgency"] = "high"
        else:
            self.user_state["urgency"] = "normal"
            
        # Track mood trajectory
        self.user_state["mood_trajectory"].append({
            "timestamp": datetime.utcnow().isoformat(),
            "emotion": emotional_state,
            "energy": energy_level
        })
        
        # Keep only last 10 mood points
        if len(self.user_state["mood_trajectory"]) > 10:
            self.user_state["mood_trajectory"] = self.user_state["mood_trajectory"][-10:]
            
        return self.user_state
        
    def _detect_emotion(self, text: str) -> str:
        """Detect emotional state from text"""
        emotion_patterns = {
            "happy": ["happy", "glad", "joyful", "excited", "great", "wonderful", "amazing", "fantastic", "love"],
            "sad": ["sad", "unhappy", "depressed", "down", "blue", "crying", "tears", "miserable"],
            "angry": ["angry", "mad", "furious", "annoyed", "irritated", "pissed", "rage", "hate"],
            "anxious": ["anxious", "worried", "nervous", "scared", "afraid", "concerned", "uneasy"],
            "confused": ["confused", "lost", "don't understand", "unclear", "puzzled", "bewildered"],
            "frustrated": ["frustrated", "stuck", "can't figure", "doesn't work", "broken", "failed"],
            "grateful": ["thank", "grateful", "appreciate", "thanks", "helpful"],
            "excited": ["excited", "can't wait", "looking forward", "thrilled", "eager"]
        }
        
        text_lower = text.lower()
        emotion_scores = {}
        
        for emotion, keywords in emotion_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                emotion_scores[emotion] = score
                
        if emotion_scores:
            return max(emotion_scores, key=emotion_scores.get)
        
        return "neutral"
        
    def _detect_energy_level(self, text: str) -> str:
        """Detect user's energy level"""
        high_energy = ["excited", "energetic", "motivated", "ready", "let's go", "pumped", "!"]
        low_energy = ["tired", "exhausted", "sleepy", "drained", "fatigue", "worn out", "need rest"]
        
        text_lower = text.lower()
        
        high_count = sum(1 for indicator in high_energy if indicator in text_lower)
        low_count = sum(1 for indicator in low_energy if indicator in text_lower)
        
        if high_count > low_count:
            return "high"
        elif low_count > high_count:
            return "low"
        else:
            return "normal"
            
    def perceive_conversation_flow(self, current_input: str, history: List[Dict]) -> Dict:
        """Analyze conversation flow and patterns"""
        
        # Detect question type
        question_type = self._classify_question(current_input)
        if question_type:
            self.conversational_context["question_types"].append(question_type)
            
        # Analyze topic consistency
        if history:
            current_topics = self._extract_topics(current_input)
            last_topics = self._extract_topics(history[-1].get("user_input", ""))
            
            if not any(topic in last_topics for topic in current_topics):
                self.conversational_context["topic_switches"] += 1
            else:
                self.conversational_context["topic_depth"] += 1
                
        # Determine interaction pattern
        if len(self.conversational_context["question_types"]) >= 3:
            recent_questions = self.conversational_context["question_types"][-3:]
            if all(q in ["how", "why", "what"] for q in recent_questions):
                self.conversational_context["interaction_pattern"] = "exploratory"
            elif all(q in ["when", "where", "specific"] for q in recent_questions):
                self.conversational_context["interaction_pattern"] = "task-focused"
            else:
                self.conversational_context["interaction_pattern"] = "mixed"
                
        # Analyze conversation speed
        if history and len(history) >= 2:
            time_diffs = []
            for i in range(1, min(len(history), 5)):
                if "timestamp" in history[i] and "timestamp" in history[i-1]:
                    t1 = datetime.fromisoformat(history[i]["timestamp"])
                    t2 = datetime.fromisoformat(history[i-1]["timestamp"])
                    time_diffs.append((t1 - t2).total_seconds())
                    
            if time_diffs:
                avg_time = sum(time_diffs) / len(time_diffs)
                if avg_time < 30:
                    self.conversational_context["conversation_flow"] = "rapid"
                elif avg_time > 120:
                    self.conversational_context["conversation_flow"] = "slow"
                else:
                    self.conversational_context["conversation_flow"] = "normal"
                    
        return self.conversational_context
        
    def _classify_question(self, text: str) -> Optional[str]:
        """Classify the type of question asked"""
        text_lower = text.lower().strip()
        
        if text_lower.endswith("?"):
            if text_lower.startswith("what"):
                return "what"
            elif text_lower.startswith("why"):
                return "why"
            elif text_lower.startswith("how"):
                return "how"
            elif text_lower.startswith("when"):
                return "when"
            elif text_lower.startswith("where"):
                return "where"
            elif text_lower.startswith("who"):
                return "who"
            elif any(text_lower.startswith(q) for q in ["is", "are", "can", "will", "should", "would"]):
                return "yes/no"
            else:
                return "specific"
        return None
        
    def _extract_topics(self, text: str) -> List[str]:
        """Extract topics from text"""
        # Simple topic extraction - in production, use NLP
        topics = []
        topic_keywords = {
            "work": ["work", "job", "office", "meeting", "project"],
            "personal": ["family", "friend", "home", "life"],
            "tech": ["computer", "phone", "app", "software"],
            "health": ["health", "sick", "doctor", "exercise"],
            "leisure": ["movie", "music", "game", "fun", "relax"]
        }
        
        text_lower = text.lower()
        for topic, keywords in topic_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                topics.append(topic)
                
        return topics
        
    def analyze_behavioral_patterns(self, interaction_history: List[Dict]) -> Dict:
        """Analyze user's behavioral patterns over time"""
        if not interaction_history:
            return self.behavioral_patterns
            
        # Analyze interaction times
        for interaction in interaction_history[-20:]:  # Last 20 interactions
            if "timestamp" in interaction:
                timestamp = datetime.fromisoformat(interaction["timestamp"])
                self.behavioral_patterns["interaction_times"].append(timestamp.hour)
                
        # Find common interaction times
        if self.behavioral_patterns["interaction_times"]:
            most_common_hour = max(set(self.behavioral_patterns["interaction_times"]), 
                                 key=self.behavioral_patterns["interaction_times"].count)
            self.behavioral_patterns["peak_interaction_time"] = most_common_hour
            
        # Analyze topic preferences
        for interaction in interaction_history:
            if "topics" in interaction:
                for topic in interaction["topics"]:
                    if topic not in self.behavioral_patterns["common_topics"]:
                        self.behavioral_patterns["common_topics"][topic] = 0
                    self.behavioral_patterns["common_topics"][topic] += 1
                    
        # Analyze communication preferences
        total_length = sum(len(i.get("user_input", "")) for i in interaction_history[-10:])
        avg_length = total_length / min(len(interaction_history), 10)
        
        if avg_length < 20:
            self.behavioral_patterns["communication_preferences"]["verbosity"] = "brief"
        elif avg_length > 100:
            self.behavioral_patterns["communication_preferences"]["verbosity"] = "detailed"
        else:
            self.behavioral_patterns["communication_preferences"]["verbosity"] = "moderate"
            
        return self.behavioral_patterns
        
    def get_perception_summary(self) -> Dict:
        """Get a comprehensive perception summary"""
        return {
            "environment": self.environmental_context,
            "user_state": self.user_state,
            "conversation": self.conversational_context,
            "patterns": self.behavioral_patterns,
            "recommendations": self._generate_recommendations()
        }
        
    def _generate_recommendations(self) -> Dict:
        """Generate recommendations based on perceptions"""
        recommendations = {
            "response_style": "balanced",
            "suggested_actions": [],
            "tone_adjustments": []
        }
        
        # Adjust based on emotional state
        if self.user_state["emotional_state"] == "anxious":
            recommendations["response_style"] = "calming"
            recommendations["tone_adjustments"].append("reassuring")
        elif self.user_state["emotional_state"] == "frustrated":
            recommendations["response_style"] = "solution-focused"
            recommendations["tone_adjustments"].append("patient")
        elif self.user_state["emotional_state"] == "happy":
            recommendations["response_style"] = "enthusiastic"
            recommendations["tone_adjustments"].append("upbeat")
            
        # Adjust based on stress level
        if self.user_state["stress_level"] == "high":
            recommendations["suggested_actions"].append("offer_stress_relief")
            recommendations["tone_adjustments"].append("supportive")
            
        # Adjust based on time of day
        if self.environmental_context["time_of_day"] == "night":
            recommendations["tone_adjustments"].append("gentle")
        elif self.environmental_context["time_of_day"] == "morning":
            recommendations["tone_adjustments"].append("energizing")
            
        # Adjust based on conversation pattern
        if self.conversational_context["interaction_pattern"] == "task-focused":
            recommendations["response_style"] = "efficient"
        elif self.conversational_context["interaction_pattern"] == "exploratory":
            recommendations["response_style"] = "educational"
            
        return recommendations


class ActionPlanner:
    """Advanced action planning and execution system"""
    
    def __init__(self, perception_engine: PerceptionEngine):
        self.perception = perception_engine
        self.action_templates = {
            "provide_information": {
                "conditions": ["question", "inquiry", "curiosity"],
                "priority": "medium",
                "execution": "search_and_explain"
            },
            "offer_assistance": {
                "conditions": ["problem", "help", "stuck", "issue"],
                "priority": "high",
                "execution": "diagnose_and_solve"
            },
            "emotional_support": {
                "conditions": ["sad", "anxious", "stressed", "upset"],
                "priority": "high",
                "execution": "empathize_and_support"
            },
            "task_management": {
                "conditions": ["remind", "schedule", "todo", "plan"],
                "priority": "medium",
                "execution": "organize_and_track"
            },
            "social_interaction": {
                "conditions": ["chat", "talk", "conversation", "hello"],
                "priority": "low",
                "execution": "engage_socially"
            }
        }
        
        self.execution_history = []
        
    def plan_actions(self, user_input: str, context: Dict, perception_summary: Dict) -> List[Dict]:
        """Create an action plan based on input and context"""
        actions = []
        
        # Analyze what actions are needed
        detected_needs = self._detect_action_needs(user_input, perception_summary)
        
        # Prioritize actions
        for need in detected_needs:
            action = {
                "type": need["type"],
                "priority": need["priority"],
                "execution_method": need["execution"],
                "parameters": self._extract_action_parameters(user_input, need["type"]),
                "timing": self._determine_timing(need, perception_summary),
                "confidence": need["confidence"]
            }
            actions.append(action)
            
        # Sort by priority and confidence
        actions.sort(key=lambda x: (x["priority"], x["confidence"]), reverse=True)
        
        # Add follow-up actions if needed
        follow_ups = self._generate_follow_up_actions(actions, perception_summary)
        actions.extend(follow_ups)
        
        return actions
        
    def _detect_action_needs(self, user_input: str, perception: Dict) -> List[Dict]:
        """Detect what actions are needed based on input"""
        detected = []
        input_lower = user_input.lower()
        
        for action_type, template in self.action_templates.items():
            confidence = 0
            matches = 0
            
            for condition in template["conditions"]:
                if condition in input_lower:
                    matches += 1
                    
            if matches > 0:
                confidence = matches / len(template["conditions"])
                detected.append({
                    "type": action_type,
                    "priority": template["priority"],
                    "execution": template["execution"],
                    "confidence": confidence
                })
                
        # Boost confidence based on perception
        user_state = perception.get("user_state", {})
        if user_state.get("emotional_state") in ["anxious", "sad", "frustrated"]:
            for action in detected:
                if action["type"] == "emotional_support":
                    action["confidence"] *= 1.5
                    action["priority"] = "urgent"
                    
        return detected
        
    def _extract_action_parameters(self, user_input: str, action_type: str) -> Dict:
        """Extract parameters needed for action execution"""
        parameters = {}
        
        if action_type == "task_management":
            # Extract time references
            time_patterns = {
                "tomorrow": timedelta(days=1),
                "next week": timedelta(weeks=1),
                "in an hour": timedelta(hours=1),
                "at (\d+)": "specific_time"
            }
            
            for pattern, value in time_patterns.items():
                if pattern in user_input.lower():
                    parameters["when"] = value
                    break
                    
            # Extract task description
            task_keywords = ["remind me to", "don't forget to", "remember to", "need to"]
            for keyword in task_keywords:
                if keyword in user_input.lower():
                    task_start = user_input.lower().find(keyword) + len(keyword)
                    parameters["task"] = user_input[task_start:].strip()
                    break
                    
        elif action_type == "provide_information":
            # Extract topic
            question_words = ["what is", "tell me about", "explain", "how does", "why"]
            for qword in question_words:
                if qword in user_input.lower():
                    topic_start = user_input.lower().find(qword) + len(qword)
                    parameters["topic"] = user_input[topic_start:].strip("? ")
                    break
                    
        return parameters
        
    def _determine_timing(self, action: Dict, perception: Dict) -> str:
        """Determine when action should be executed"""
        user_state = perception.get("user_state", {})
        
        if user_state.get("urgency") == "high" or action["priority"] == "urgent":
            return "immediate"
        elif action["priority"] == "high":
            return "soon"
        else:
            return "when_appropriate"
            
    def _generate_follow_up_actions(self, primary_actions: List[Dict], perception: Dict) -> List[Dict]:
        """Generate follow-up actions based on primary actions"""
        follow_ups = []
        
        for action in primary_actions:
            if action["type"] == "emotional_support":
                # Add check-in action
                follow_ups.append({
                    "type": "check_emotional_state",
                    "priority": "medium",
                    "execution_method": "follow_up_check",
                    "parameters": {"after_minutes": 10},
                    "timing": "delayed",
                    "confidence": 0.8
                })
                
            elif action["type"] == "task_management":
                # Add reminder confirmation
                follow_ups.append({
                    "type": "confirm_task_completion",
                    "priority": "low",
                    "execution_method": "task_follow_up",
                    "parameters": action["parameters"],
                    "timing": "after_task_time",
                    "confidence": 0.7
                })
                
        return follow_ups
        
    def execute_action_plan(self, actions: List[Dict], context: Dict) -> Dict:
        """Execute the planned actions and return results"""
        results = {
            "executed_actions": [],
            "pending_actions": [],
            "failed_actions": [],
            "overall_success": True
        }
        
        for action in actions:
            try:
                if action["timing"] == "immediate":
                    # Execute now
                    result = self._execute_single_action(action, context)
                    results["executed_actions"].append({
                        "action": action,
                        "result": result,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    # Schedule for later
                    results["pending_actions"].append(action)
                    
            except Exception as e:
                logger.error(f"Action execution failed: {e}")
                results["failed_actions"].append(action)
                results["overall_success"] = False
                
        # Record execution history
        self.execution_history.append({
            "timestamp": datetime.utcnow().isoformat(),
            "actions": actions,
            "results": results
        })
        
        return results
        
    def _execute_single_action(self, action: Dict, context: Dict) -> Dict:
        """Execute a single action"""
        execution_method = action["execution_method"]
        
        if execution_method == "search_and_explain":
            return {
                "status": "completed",
                "action_taken": "searched_information",
                "response_modifier": "informative"
            }
        elif execution_method == "empathize_and_support":
            return {
                "status": "completed",
                "action_taken": "provided_emotional_support",
                "response_modifier": "empathetic"
            }
        elif execution_method == "organize_and_track":
            return {
                "status": "completed",
                "action_taken": "created_reminder",
                "response_modifier": "organized"
            }
        else:
            return {
                "status": "completed",
                "action_taken": execution_method,
                "response_modifier": "helpful"
            }