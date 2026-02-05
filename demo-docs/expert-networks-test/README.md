# Expert Networks Test Data

This folder contains sample emails for validating the Expert Network Aggregator functionality.

## Test Scenarios

### 1. Long Email Thread with Duplicates (`01_long_email_thread.txt`)

**Purpose**: Test extraction from a long email thread (20-30 replies) with the same experts mentioned multiple times as their status updates.

**Expected Behavior**:
- Extract 4 unique experts: Dr. Wei Chen, Jennifer Park, Robert Anderson, Marcus Williams
- **Dr. Wei Chen** should appear once with:
  - Latest conflict status: "cleared" (was "pending")
  - Availability: Thursday Jan 18, 3-5pm EST or Friday Jan 19, 10am-12pm EST
- **Robert Anderson** should be marked as "declined" (competitor conflict)
- Extraction notes should mention that duplicate expert mentions were merged

**Validation Checklist**:
- [ ] Each expert appears exactly once
- [ ] Dr. Chen's status shows final "cleared" state
- [ ] Screener responses are captured for Chen, Park, Williams
- [ ] Network correctly identified as AlphaSights

---

### 2. Two-Email Update Scenario (`02a_initial_experts.txt` + `02b_followup_updates.txt`)

**Purpose**: Test the system's ability to handle follow-up emails that update existing experts.

**Sequence**:
1. **Ingest `02a_initial_experts.txt` first** - Creates 3 experts
2. **Ingest `02b_followup_updates.txt` second** - Updates existing experts

**Expected Behavior After First Email**:
- 3 experts created: Dr. Amanda Foster, James Rodriguez, Dr. Sarah Kim
- Amanda Foster: conflict status "pending"
- James Rodriguez: conflict status "cleared"
- Dr. Sarah Kim: conflict status "pending", limited availability

**Expected Behavior After Second Email (Updates)**:
- **No new experts created** - all should match existing
- Dr. Amanda Foster: 
  - Conflict updated to "cleared"
  - Availability updated with specific times
- Dr. Sarah Kim:
  - Conflict updated to "cleared"
  - Availability updated
  - Additional screener responses added (AI questions)
- James Rodriguez: No changes
- Change summary should show: 0 added, 2-3 updated, 0 merged

**Validation Checklist**:
- [ ] Second ingestion creates 0 new experts
- [ ] Foster and Kim show updated conflict status
- [ ] Kim has additional screener responses
- [ ] Change summary reflects updates only

---

### 3. Multi-Network Same Expert (`03a_glg_experts.txt` + `03b_alphasights_experts.txt`)

**Purpose**: Test handling of the same expert sourced from multiple networks.

**Scenario**: Michael Torres appears in both GLG and AlphaSights emails.

**Sequence**:
1. **Ingest `03a_glg_experts.txt` (GLG)** - Creates Michael Torres and Lisa Park
2. **Ingest `03b_alphasights_experts.txt` (AlphaSights)** - Should match Michael Torres, add Robert Kim

**Expected Behavior**:
- Michael Torres should be deduplicated/matched:
  - Same canonical record for both networks
  - ExpertSource records from both GLG and AlphaSights
  - Network-specific screener responses preserved separately
- Lisa Park: GLG only
- Robert Kim: AlphaSights only

**Validation Checklist**:
- [ ] Michael Torres appears once in tracker
- [ ] Has sources from both GLG and AlphaSights
- [ ] Both networks' screener responses are preserved
- [ ] Different availability windows from each network are captured
- [ ] Deduplication correctly identified the match (high confidence)

---

## Using This Test Data

### Quick Test Flow

1. Create a new project with hypothesis: "Evaluating payment technology companies for investment"

2. Set up screener config with questions:
   - "What payment rails do you have direct experience with?"
   - "What's your perspective on emerging payment trends?"
   
3. Ingest emails in order for each test scenario

4. Verify expected behavior using the tracker and change summary

### Verifying Smart Screening

For projects with screener configuration:
- Experts with detailed screener responses should get "strong" or "mixed" grades
- Experts missing screener responses should get "weak" grades
- The screening rationale should reference the configured rubric

### Verifying Deduplication

Check the dedupe candidates list for:
- High confidence matches (>85%) should be auto-merged
- Lower confidence matches should appear in "Needs Review"
- Name variations like "Dr. Wei Chen" vs "Wei Chen" should still match
