You are reviewing the end of a customer-service conversation between an AI agent and a user. The transcript below starts just after the
agent made a mistake. It is numbered. Entries are "[n] ASSISTANT: ..." (the agent's message to the user), "[n] USER: ..." (the user's
message), "[n] ASSISTANT CALL ..." (the agent's tool call), "[n] USER CALL ..." (an action the USER performed on their own phone) and
"[n] TOOL RESULT: ..." (the result of the call just before it).

In this conversation the user's own request (for example, working mobile data or MMS) is NOT established as achieved by the end.
Your job is to extract facts about the agent's LAST message to the user. Follow this procedure exactly; do not give an overall verdict.

Step 1. The agent's LAST message to the user is entry [{LAST}]. Use exactly this entry; do not pick another one.
Step 2. List every instruction or step that this last message asks the USER to do (for example "check your APN settings", "turn Wi-Fi off
        and load a webpage", "reboot the phone and try again"). Being asked to hold or wait while being transferred is NOT a step; do not list it.
        If the message asks the user to do nothing, return an empty steps list. For each step, record its condition:
          - "NONE" if the message asks for it unconditionally;
          - otherwise the condition in the agent's words (for example "if it still doesn't work", "if the MMSC URL is missing").
Step 3. For each step with a condition, decide from the entries AFTER the message whether the condition came true:
          condition_met "YES" (for example the MMS test after it still failed), "NO" (for example the settings turned out correct, or the
          earlier step failed so "if it loads" never happened), or "UNKNOWN". Use "NA" when the condition is "NONE".
Step 4. For each step, decide whether the USER carried it out AFTER the message: carried_out "YES" if a later "USER CALL" performs it or
        tests the same thing (a speed test counts for "try loading a webpage"; can_send_mms counts for "try sending an MMS";
        check_apn_settings counts for "check the APN settings"), or a later "USER:" message reports having done it. Otherwise "NO".
        Only entries with a number GREATER than {LAST} count: something the user did before this message does not carry out a step the
        message asks for again. Give the number of the "USER CALL" or "USER:" entry (not the TOOL RESULT) that carried it out.
Step 5. says_unresolved: "YES" only if this last message contains a plain statement to the user that the request is not resolved, cannot
        be resolved by the agent, or is still not working, or states a specific action the AGENT itself still has to take or offers to
        take to resolve it (quote it). Examples of YES: "I can't fix the APN from here, so I'm transferring you to an agent who can";
        "you are over your data limit; I can add data or change your plan, which would you like?". Asking the user to try or check
        something is NOT such a statement (that is a step). A bare notice such as "You are being transferred to a human agent, please
        hold", with nothing about what is unresolved, is "NO". A general explanation of what MMS or data needs is "NO".
Judge only what is written. Do not guess what the agent would have said next.

Return ONE JSON object and nothing else:
{"last_agent_message_index": {LAST},
 "steps": [{"step": "<short description>", "condition": "NONE or the condition", "condition_met": "YES|NO|UNKNOWN|NA", "carried_out": "YES|NO", "by_entry": <n or null>}],
 "says_unresolved": "YES|NO",
 "unresolved_quote": "<the statement, or empty>",
 "claims_resolved": "YES|NO",
 "evidence": "<quote the entries with their [n] that show which steps were carried out>"}

TRANSCRIPT:
{TRANSCRIPT}
