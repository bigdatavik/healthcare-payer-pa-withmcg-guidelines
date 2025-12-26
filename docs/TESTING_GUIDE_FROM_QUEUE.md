# Quick Testing Guide - From Queue UI

## 🚀 Quick Start (5 Minutes)

### Access the App
```
URL: https://pa-dashboard-dev-984752964297111.11.azure.databricksapps.com
```

### Test Scenario 1: Load and Process PA Request

1. **Open App** → Navigate to **"From Queue"** tab
2. **Verify**: Should see `✅ 10 pending requests found`
3. **Click**: Any request (e.g., "PA-2024-12-26-001 | PT00001 | CPT 29881")
4. **Observe**: 
   - Agent workflow executes automatically
   - MCG questions retrieved
   - Clinical records loaded
   - Answers generated
   - Decision calculated
5. **Result**: Decision saved to database (APPROVED/MANUAL_REVIEW/DENIED)

### Test Scenario 2: Demo Reset (All Requests)

1. **Process** 2-3 requests using Test Scenario 1
2. **Scroll** to "Demo Reset" section at bottom
3. **Click**: "🔄 Reset All 10 Demo Requests to Pending"
4. **Verify**: 
   - Success message: `✅ All 10 demo requests reset to PENDING`
   - Queue refreshes automatically
   - All 10 requests back in pending state

### Test Scenario 3: Demo Reset (Individual Request)

1. **Process** 1-2 requests
2. **Scroll** to "Processed Demo Requests" section
3. **Click**: Any processed request (e.g., "✅ PA-2024-12-26-001 | PT00001 | APPROVED (75%)")
4. **Verify**:
   - Success message: `✅ PA-2024-12-26-001 reset to PENDING`
   - Request reappears in pending queue

### Test Scenario 4: Sample Cases (Verify Unchanged)

1. **Click** "Sample Cases" tab
2. **Click**: "Knee Arthroscopy (APPROVED - 75%)"
3. **Verify**: 
   - Loads PT00001 data
   - Agent workflow executes
   - Decision: APPROVED (75%)

### Test Scenario 5: Custom Request (Verify Unchanged)

1. **Click** "Custom" tab
2. **Verify**: Pre-filled with PT00001 sample data
3. **Modify** any field (e.g., change Patient ID to "PT00016")
4. **Click**: "📝 Use Custom Request"
5. **Verify**: Loads modified request and processes

## 🎯 Expected Results

### From Queue Tab
- ✅ **Queue Loading**: 10 pending requests display with urgency icons
- ✅ **Request Loading**: Click → loads → processes → saves decision
- ✅ **Reset All**: Resets all 10 demo requests to pending
- ✅ **Reset Individual**: Resets single request to pending
- ✅ **Auto-Refresh**: Queue updates automatically after reset

### Sample Cases Tab
- ✅ **PT00001 (Knee Arthroscopy)**: APPROVED (75%)
- ✅ **PT00016 (Total Knee Replacement)**: MANUAL_REVIEW (50%)
- ✅ **PT00025 (Lumbar Fusion)**: DENIED (0%)

### Custom Tab
- ✅ **Pre-filled**: PT00001 sample data
- ✅ **Custom Entry**: Accepts any patient/procedure/diagnosis
- ✅ **Processing**: Executes agent workflow for custom data

## 🐛 Common Issues

### Issue: "No pending PA requests in queue"
**Fix**: All requests were processed. Click "🔄 Reset All 10 Demo Requests to Pending"

### Issue: "INSUFFICIENT_PERMISSIONS"
**Fix**: Run `./grant_permissions.sh` from project root

### Issue: Old UI showing
**Fix**: Hard refresh browser (Cmd+Shift+R or Ctrl+Shift+R)

### Issue: Reset doesn't work
**Fix**: Check app has `MODIFY` permission on `authorization_requests` table

## 📊 Demo Flow (Recommended Order)

### For Executive Audience
1. **Sample Cases** → Show quick wins (PT00001 APPROVED)
2. **From Queue** → Show real-world workflow
3. **Demo Reset** → Show ease of re-running demo

### For Technical Audience
1. **From Queue** → Explain data loading from Unity Catalog
2. **Agent Workflow** → Show LangGraph orchestration
3. **Traceability** → Show MCG Q&A details
4. **Custom** → Show edge case handling

### For Clinical Audience
1. **Sample Cases** → Show specific clinical scenarios
2. **MCG Questions** → Explain guideline criteria
3. **Evidence** → Show clinical record matching
4. **Decision Logic** → Explain confidence thresholds

## 🔄 Quick Reset Between Demos

```bash
# Option 1: In-App (Recommended)
# Click "🔄 Reset All 10 Demo Requests to Pending" in From Queue tab

# Option 2: Via SQL (if app unavailable)
databricks sql execute \
  --warehouse-id 148ccb90800933a1 \
  --catalog healthcare_payer_pa_withmcg_guidelines_dev \
  --schema main \
  --query "
UPDATE authorization_requests
SET decision = NULL,
    decision_date = NULL,
    confidence_score = NULL,
    mcg_code = NULL,
    explanation = NULL,
    reviewed_by = NULL,
    updated_at = CURRENT_TIMESTAMP()
WHERE request_id LIKE 'PA-2024-12-26-%'
"
```

## 📝 Testing Checklist

- [ ] From Queue tab loads 10 pending requests
- [ ] Click request → loads → processes → saves decision
- [ ] Reset All → all 10 requests reset to pending
- [ ] Reset Individual → single request resets to pending
- [ ] Sample Cases tab still works (all 3 cases)
- [ ] Custom tab still works (pre-filled and custom entry)
- [ ] Traceability table shows MCG Q&A details
- [ ] Decision saved to database (query `authorization_requests`)
- [ ] Audit trail saved to `pa_audit_trail` (if implemented)

## 🎬 Recording Demo Tips

1. **Start Fresh**: Reset all requests before recording
2. **Show Flow**: Queue → Load → Process → Decision
3. **Explain**: Narrate each step (MCG questions, evidence, decision)
4. **Highlight**: Show traceability table for transparency
5. **Reset**: Demonstrate quick reset for next demo

---

**App URL**: https://pa-dashboard-dev-984752964297111.11.azure.databricksapps.com
**Status**: ✅ RUNNING (Deployment succeeded)
**Last Updated**: Dec 26, 2025

