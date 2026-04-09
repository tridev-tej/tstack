---
description: Deep research with Graph of Thoughts - explores multiple paths in parallel, scores them, finds optimal solutions
---

# Deep Research Agent with Graph of Thoughts

This agent explores multiple research paths in parallel, scores them, and finds optimal solutions through graph traversal.

## Preparation

All produced documents go inside `/RESEARCH/[project_name]/` where project_name is based on the inquiry. Break down into smaller documents to avoid context limitations. Complete all defined tasks and track completion.

## The 7-Phase Deep Research Process

### Phase 1: Question Scoping
- Clarify the research question with the user
- Define output format and success criteria
- Identify constraints and desired tone
- Create unambiguous query with clear parameters

### Phase 2: Retrieval Planning
- Break main question into subtopics
- Generate specific search queries
- Select appropriate data sources
- Create research plan for user approval
- Use GoT to model the research as a graph of operations

### Phase 3: Iterative Querying
- Execute searches systematically
- Navigate and extract relevant information
- Formulate new queries based on findings
- Use multiple search modalities (web search, file analysis, etc.)
- Apply GoT operations for complex reasoning

### Phase 4: Source Triangulation
- Compare findings across multiple sources
- Validate claims with cross-references
- Handle inconsistencies
- Assess source credibility
- Use GoT scoring functions to evaluate information quality

### Phase 5: Knowledge Synthesis
- Structure content logically
- Write comprehensive sections
- Include inline citations for every claim
- Add data visualizations when relevant
- Use GoT to optimize information organization

### Phase 6: Quality Assurance
- Check for hallucinations and errors
- Verify all citations match content
- Ensure completeness and clarity
- Apply Chain-of-Verification techniques
- Use GoT ground truth operations for validation

### Phase 7: Output & Packaging
- Format for optimal readability
- Include executive summary
- Create proper bibliography
- Export in requested format

## Understanding Graph of Thoughts

Graph of Thoughts is a reasoning framework where:
- **Thoughts = Nodes**: Each research finding or synthesis is a node
- **Edges = Dependencies**: Connect parent thoughts to children
- **Transformations**: Operations that create (Generate), merge (Aggregate), or improve (Refine) thoughts
- **Scoring**: Every thought is evaluated 0-10 for quality
- **Pruning**: Low-scoring branches are abandoned
- **Frontier**: Active nodes available for expansion

### Core Concepts

1. **Graph Structure**:
   - Each research finding is a node with a unique ID
   - Nodes have scores (0-10) indicating quality
   - Edges connect parent thoughts to child thoughts
   - The frontier contains active nodes for expansion

2. **Transformation Operations**:
   - **Generate(k)**: Create k new thoughts from a parent
   - **Aggregate(k)**: Merge k thoughts into one stronger thought
   - **Refine(1)**: Improve a thought without adding new content
   - **Score**: Evaluate thought quality
   - **KeepBestN(n)**: Prune to keep only top n nodes per level

3. **Research Quality Metrics**:
   - Citation density and accuracy
   - Source credibility
   - Claim verification
   - Comprehensiveness
   - Logical coherence

## Implementation Tools

### Core Tools:
1. **WebSearch**: Built-in web search capability for finding relevant sources
2. **WebFetch**: For extracting and analyzing content from specific URLs
3. **Read/Write**: For managing research documents locally
4. **Task**: For spawning autonomous agents for complex multi-step operations
5. **TodoWrite**: For tracking research progress

### Web Research Strategy:
- **Primary**: Use WebSearch tool for general web searches
- **Secondary**: Use WebFetch for extracting content from specific URLs
- **Advanced**: Use mcp__puppeteer__ for sites requiring interaction or JavaScript rendering

## Graph of Thoughts Research Strategy

The system implements GoT using Task agents that act as transformation operations. When you request deep research, a controller agent maintains the graph state and deploys specialized agents to explore, refine, and aggregate research paths.

### Step 1: Create Research Plan
Break down the main research question into specific subtopics:
- Subtopic 1: Current state and trends
- Subtopic 2: Key challenges and limitations
- Subtopic 3: Future developments and predictions
- Subtopic 4: Case studies and real-world applications
- Subtopic 5: Expert opinions and industry perspectives

### Step 2: Launch Parallel Agents
Use multiple Task tool invocations in a single response to launch agents simultaneously. Each agent should receive:
- Clear description of their research focus
- Specific instructions on what to find
- Expected output format

### Step 3: Coordinate Results
After agents complete their tasks:
- Compile findings from all agents
- Identify overlaps and contradictions
- Synthesize into coherent narrative
- Maintain source attribution from each agent

### Multi-Agent Deployment Example

When researching a topic, deploy agents as follows:

**Agent 1**: "Research current applications in the domain"
**Agent 2**: "Find challenges and ethical concerns"
**Agent 3**: "Investigate future innovations"
**Agent 4**: "Gather case studies of successful implementations"
**Agent 5**: "Cross-reference and verify key statistics"

### Best Practices for Multi-Agent Research

1. **Clear Task Boundaries**: Each agent should have a distinct focus to minimize redundancy
2. **Comprehensive Prompts**: Include all necessary context in agent prompts
3. **Parallel Execution**: Launch all agents in one response for maximum efficiency
4. **Result Integration**: Plan how to merge findings before launching agents
5. **Quality Control**: Always include at least one verification agent

## GoT Agent Templates

### Generate Agent Template
```
Execute Graph of Thoughts research for: [specific aspect] of [main topic]

1. WebSearch for relevant sources (minimum 5)
2. Score each source quality (1-10)
3. WebFetch top 3 sources
4. Synthesize findings into coherent thought (200-400 words)
5. Self-score your thought (0-10) based on:
   - Claim accuracy
   - Citation density
   - Novel insights
   - Coherence

Return: thought, score, sources, operation type
```

### Aggregate Agent Template
```
Combine [k] thoughts into ONE stronger unified thought that:
- Preserves all important claims
- Resolves contradictions
- Maintains all citations
- Achieves higher quality than any input

Self-score the result (0-10).
```

### Refine Agent Template
```
Improve thought by:
1. Fact-check claims using WebSearch
2. Add missing context/nuance
3. Strengthen weak arguments
4. Fix citation issues
5. Enhance clarity

Do NOT add new major points - only refine existing content.
Self-score improvement (0-10).
```

## Research Quality Checklist

- [ ] Every claim has a verifiable source
- [ ] Multiple sources corroborate key findings
- [ ] Contradictions are acknowledged and explained
- [ ] Sources are recent and authoritative
- [ ] No hallucinations or unsupported claims
- [ ] Clear logical flow from evidence to conclusions
- [ ] Proper citation format throughout

## Advanced Research Methodologies

### Chain-of-Density (CoD) Summarization
When processing sources, use iterative refinement to increase information density:
1. First pass: Extract key points (low density)
2. Second pass: Add supporting details and context
3. Third pass: Compress while preserving all critical information
4. Final pass: Maximum density with all essential facts and citations

### Chain-of-Verification (CoVe)
To prevent hallucinations:
1. Generate initial research findings
2. Create verification questions for each claim
3. Search for evidence to answer verification questions
4. Revise findings based on verification results
5. Repeat until all claims are verified

### ReAct Pattern (Reason + Act)
Agents should follow this loop:
1. **Reason**: Analyze what information is needed
2. **Act**: Execute search or retrieval action
3. **Observe**: Process the results
4. **Reason**: Determine if more information needed
5. **Repeat**: Continue until sufficient evidence gathered

### Multi-Agent Orchestration
For complex topics, deploy specialized agents:
- **Planner Agent**: Decomposes research into subtopics
- **Search Agents**: Execute queries and retrieve sources
- **Synthesis Agents**: Combine findings from multiple sources
- **Critic Agents**: Verify claims and check for errors
- **Editor Agent**: Polishes final output

## Citation Requirements & Source Traceability

### Mandatory Citation Standards

**Every factual claim must include:**
1. **Author/Organization** - Who made this claim
2. **Date** - When the information was published
3. **Source Title** - Name of paper, article, or report
4. **URL/DOI** - Direct link to verify the source
5. **Page Numbers** - For lengthy documents (when applicable)

### Citation Formats

**Academic Papers:**
```
(Author et al., Year, p. XX) with full citation in references
Example: (Smith et al., 2023, p. 145)
Full: Smith, J., Johnson, K., & Lee, M. (2023). "Title of Paper." Journal Name, 45(3), 140-156. https://doi.org/10.xxxx/xxxxx
```

**Web Sources:**
```
(Organization, Year, Section Title)
Example: (NIH, 2024, "Treatment Guidelines")
Full: National Institutes of Health. (2024). "Treatment Guidelines for Metabolic Syndrome." Retrieved [date] from https://www.nih.gov/specific-page
```

### Source Quality Ratings
- **A**: Peer-reviewed RCTs, systematic reviews, meta-analyses
- **B**: Cohort studies, case-control studies, clinical guidelines
- **C**: Expert opinion, case reports, mechanistic studies
- **D**: Preliminary research, preprints, conference abstracts
- **E**: Anecdotal, theoretical, or speculative

### Red Flags for Unreliable Sources
- No author attribution
- Missing publication dates
- Broken or suspicious URLs
- Claims without data
- Conflicts of interest not disclosed
- Predatory journals
- Retracted papers (check RetractionWatch)

## Output Structure

```
RESEARCH/
└── [topic_name]/
    ├── README.md (Overview and navigation guide)
    ├── executive_summary.md (1-2 page summary)
    ├── full_report.md (Comprehensive findings)
    ├── data/
    │   ├── raw_data.csv
    │   ├── processed_data.json
    │   └── statistics_summary.md
    ├── visuals/
    │   ├── charts/
    │   ├── graphs/
    │   └── infographics/
    ├── sources/
    │   ├── bibliography.md
    │   ├── source_summaries.md
    │   └── screenshots/
    ├── research_notes/
    │   ├── agent_1_findings.md
    │   ├── agent_2_findings.md
    │   └── synthesis_notes.md
    └── appendices/
        ├── methodology.md
        ├── limitations.md
        └── future_research.md
```

## User Interaction Protocol

### Required Information Checklist

Before starting research, clarify:

1. **Core Research Question**
   - Main topic or question to investigate
   - Specific aspects or angles of interest
   - What problem are you trying to solve?

2. **Output Requirements**
   - Desired format (report, presentation, analysis, etc.)
   - Length expectations (executive summary vs comprehensive report)
   - Visual requirements (charts, graphs, diagrams, images)

3. **Scope & Boundaries**
   - Geographic focus (global, specific countries/regions)
   - Time period (current, historical, future projections)
   - Industry or domain constraints
   - What should be excluded from research?

4. **Sources & Credibility**
   - Preferred source types (academic, industry, news, etc.)
   - Any sources to prioritize or avoid
   - Required credibility level

5. **Special Requirements**
   - Specific data or statistics needed
   - Comparison frameworks to use
   - Regulatory or compliance considerations
   - Target audience for the research

## Graph Traversal Strategy

The Controller maintains the graph and decides which transformations to apply:

1. **Early Depth (0-2)**: Aggressive Generate(3) to explore search space
2. **Mid Depth (2-3)**: Mix of Generate for promising paths + Refine for weak nodes
3. **Late Depth (3-4)**: Aggregate best branches + final Refine
4. **Pruning**: Keep only top 5 nodes per depth level
5. **Termination**: When best node scores 9+ or depth exceeds 4

## GoT Execution Flow Example

### Iteration 1: Initialize and Explore
1. **Controller Agent** creates root node: "Research [TOPIC]"
2. **Generate(3)** deploys 3 parallel agents exploring different angles
3. **Results**: 3 thoughts with scores
4. **Graph state** saved with frontier sorted by score

### Iteration 2: Deepen Best Paths
1. **Controller** examines frontier, decides:
   - High score (>8): Generate(3) for deeper exploration
   - Medium score (6-8): Generate(2)
   - Low score (<6): Refine(1) to improve
2. **Multiple agents** deployed in parallel
3. Track best results

### Iteration 3: Aggregate Strong Branches
1. **Controller** sees multiple high scores
2. **Aggregate(3)** merges best thoughts into comprehensive synthesis
3. **Score** the aggregated result

### Iteration 4: Final Polish
1. **Refine(1)** enhances clarity and completeness
2. **Final thought** scored
3. **Output**: Best path through graph becomes research report

## Key Principles

### Iterative Refinement
Deep research is not linear - it's a continuous loop of:
1. **Search**: Find relevant information
2. **Read**: Extract key insights
3. **Refine**: Generate new queries based on findings
4. **Verify**: Cross-check claims across sources
5. **Synthesize**: Combine into coherent narrative
6. **Repeat**: Continue until comprehensive coverage

### Why This Outperforms Manual Research
- **Breadth**: AI can process 20+ sources in minutes vs days for humans
- **Depth**: Multi-step reasoning uncovers non-obvious connections
- **Consistency**: Systematic approach ensures no gaps
- **Traceability**: Every claim linked to source
- **Efficiency**: Handles low-level tasks, freeing humans for analysis

---

**To start deep research, simply say:**
"Deep research [your topic]"

The agent will:
1. Ask clarifying questions if needed
2. Deploy a GoT Controller to manage the graph
3. Launch transformation agents (Generate, Refine, Aggregate)
4. Explore multiple research paths with scoring
5. Deliver the optimal research findings
