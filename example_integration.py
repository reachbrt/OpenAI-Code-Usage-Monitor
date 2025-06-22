#!/usr/bin/env python3
"""
Example integration of OpenAI Usage Tracker with actual OpenAI API calls.
This shows how to track token usage in your own applications.
"""

import os
import openai
from openai_usage_monitor import OpenAIUsageTracker

# Model pricing (as of 2024 - check OpenAI pricing page for current rates)
MODEL_PRICING = {
    'gpt-4': {'prompt': 0.00003, 'completion': 0.00006},
    'gpt-4-turbo': {'prompt': 0.00001, 'completion': 0.00003},
    'gpt-3.5-turbo': {'prompt': 0.0000015, 'completion': 0.000002},
    'gpt-4o': {'prompt': 0.000005, 'completion': 0.000015},
    'gpt-4o-mini': {'prompt': 0.00000015, 'completion': 0.0000006},
}

def calculate_cost(model, prompt_tokens, completion_tokens):
    """Calculate cost based on model and token usage."""
    if model not in MODEL_PRICING:
        # Default to gpt-4 pricing if model not found
        model = 'gpt-4'
    
    pricing = MODEL_PRICING[model]
    prompt_cost = prompt_tokens * pricing['prompt']
    completion_cost = completion_tokens * pricing['completion']
    return prompt_cost + completion_cost

def make_tracked_openai_call(tracker, session_id, messages, model='gpt-4', **kwargs):
    """
    Make an OpenAI API call and automatically track the usage.
    
    Args:
        tracker: OpenAIUsageTracker instance
        session_id: Current session ID
        messages: Messages for the API call
        model: Model to use
        **kwargs: Additional arguments for OpenAI API
    
    Returns:
        OpenAI API response
    """
    try:
        # Make the API call
        response = openai.ChatCompletion.create(
            model=model,
            messages=messages,
            **kwargs
        )
        
        # Extract token usage
        usage = response['usage']
        prompt_tokens = usage['prompt_tokens']
        completion_tokens = usage['completion_tokens']
        
        # Calculate cost
        cost = calculate_cost(model, prompt_tokens, completion_tokens)
        
        # Log the usage
        tracker.log_api_call(
            session_id=session_id,
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost=cost
        )
        
        print(f"✅ API call logged: {prompt_tokens + completion_tokens} tokens, ${cost:.4f}")
        
        return response
        
    except Exception as e:
        print(f"❌ Error making API call: {e}")
        raise

def main():
    """Example usage of the tracked OpenAI calls."""
    
    # Get API key
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ Please set OPENAI_API_KEY environment variable")
        return
    
    # Set up OpenAI
    openai.api_key = api_key
    
    # Initialize tracker
    tracker = OpenAIUsageTracker(api_key)
    
    # Create a new session
    session_id = tracker.create_session("example_session")
    print(f"📊 Created session: {session_id}")
    
    # Example conversations
    conversations = [
        {
            "messages": [
                {"role": "user", "content": "What is the capital of France?"}
            ],
            "model": "gpt-3.5-turbo"
        },
        {
            "messages": [
                {"role": "user", "content": "Explain quantum computing in simple terms."}
            ],
            "model": "gpt-4"
        },
        {
            "messages": [
                {"role": "user", "content": "Write a short poem about programming."}
            ],
            "model": "gpt-4o-mini"
        }
    ]
    
    print("\n🚀 Making tracked API calls...")
    
    for i, conv in enumerate(conversations, 1):
        print(f"\n📞 Call {i}: {conv['model']}")
        try:
            response = make_tracked_openai_call(
                tracker=tracker,
                session_id=session_id,
                messages=conv["messages"],
                model=conv["model"],
                max_tokens=150,
                temperature=0.7
            )
            
            # Print the response
            content = response['choices'][0]['message']['content']
            print(f"🤖 Response: {content[:100]}...")
            
        except Exception as e:
            print(f"❌ Failed: {e}")
    
    # Show session summary
    data = tracker.get_local_usage_data()
    if data['active_session']:
        session = data['active_session']
        print(f"\n📊 Session Summary:")
        print(f"   Total Tokens: {session[4]:,}")
        print(f"   Total Cost: ${session[7]:.4f}")
        print(f"   API Calls: {len(data['recent_calls'])}")
    
    print(f"\n✅ Example complete! Run the monitor to see real-time tracking:")
    print(f"   ./openai_usage_monitor.py")

if __name__ == "__main__":
    main()
