# CareerCoach AI Architecture

## Intelligence pipeline

Resume + JD + role
        |
        v
Profile Extractor
        |
        +--> skills
        +--> projects
        +--> claimed achievements
        +--> seniority
        |
        v
Competency Mapper
        |
        +--> technical
        +--> project depth
        +--> behavioral
        +--> communication
        |
        v
Interview Planner
        |
        v
Adaptive Interview Agent
        |
        +--> ask question
        +--> capture answer
        +--> evaluate answer
        +--> decide follow-up
        |
        v
Candidate Memory
        |
        +--> strengths
        +--> weaknesses
        +--> recurring mistakes
        +--> topics to revisit

## Question generation policy
Questions should be generated from:
1. Resume claims
2. Job-description requirements
3. Role competency maps
4. Original internal question templates
5. Prior candidate weaknesses

Do not copy proprietary question banks or scrape sites for verbatim reproduction.

## Evaluation dimensions
Technical correctness
Technical depth
Reasoning
Trade-offs
Project ownership
Specificity
Communication clarity
Structure
Confidence/prosody (voice phase)
Filler words (voice phase)

## Future stack
Frontend: Next.js + TypeScript + Tailwind
API: Python + FastAPI
Database: Postgres/Supabase
LLM: provider abstraction
Speech-to-text: provider abstraction
Text-to-speech: provider abstraction
Payments: Razorpay/Stripe
Deployment: Vercel + managed Python API

## Product moat
Every completed interview produces structured signals:
candidate skill -> question -> answer -> evidence -> score -> weakness -> improvement over time.

This longitudinal competency graph is more defensible than a static question bank.
