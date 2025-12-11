# Troubleshooting Guide

## Current Status

✅ **Server Running**: http://localhost:8000  
✅ **Backend Fixed**: API now returns `dimension_explanations`  
✅ **Frontend Fixed**: Explain buttons and modal implemented  
✅ **Debug Logging Added**: Console will show explanation data

## Issues & Solutions

### 1. Explain Button Not Working ✨

**What I've Fixed:**
- ✅ Added `dimension_explanations` to API response (`api/agent.py` line 169)
- ✅ Created `openExplanation()` and `closeExplanation()` functions in `intake.js`
- ✅ Added side-panel modal HTML in `intake.html` (lines 215-250)
- ✅ Added **debug logging** to track explanation data flow

**How to Test:**
1. **Open**: http://localhost:8000/intake
2. **Submit an idea** (e.g., "A small AI sensor that predicts queue lengths")
3. **Wait for analysis** to complete (~10 seconds)
4. **Open Browser Console** (F12 → Console tab)
5. **Look for these logs:**
   ```
   🔍 Dimensional Analysis Data:
   - Dimensions: {problem_clarity: 0.72, ...}
   - Explanations: {problem_clarity: "The description clearly...", ...}
   ```
6. **Hover over any dimension card** → You should see ✨ Explain button
7. **Click "Explain"** → Purple side panel should slide in from right

**If Explain is still empty:**
- Check Console for: `"Explanations: {}"` (means API didn't send data)
- Look for JavaScript errors in Console
- Check Network tab → `/api/v1/agent/invoke` → Response → Should have `dimension_explanations` field

### 2. Cofounder Page Empty 👥

**What I've Fixed:**
- ✅ Added instructional UI element (`cf-instructions`) in `cofounder.html`
- ✅ Updated `displayMatches()` to hide instructions when matches load
- ✅ The page already has all necessary HTML/JS

**How the Page Works:**
1. **Visit**: http://localhost:8000/cofounder
2. **You should see** a big instructional box:
   ```
   👆
   Ready to Find Your Cofounder?
   1️⃣ Select your profile from the dropdown above
   2️⃣ Click the "Find Matches" button
   ```
3. **Select a profile** from dropdown (top left)
4. **Click "Find Matches"** button
5. **Wait 1-2 seconds** → Instructions disappear, match cards appear

**The page is NOT broken** - it's just waiting for you to:
- Select a profile
- Click the button

**If still empty after clicking:**
- Check Console for: `"📺 displayMatches called with X matches"`
- Look for errors in Console
- Check Network tab → `/matching/matches/12` → Should return match data

## Debug Checklist

### For Explain Functionality:
- [ ] Server running on localhost:8000
- [ ] Browser console open (F12)
- [ ] Idea submitted and analysis complete
- [ ] Console shows: `"🔍 Dimensional Analysis Data"`
- [ ] Console shows: `"Explanations: {problem_clarity: '...', ...}"`
- [ ] Hover over dimension card shows Explain button
- [ ] Click Explain opens purple side panel

### For Cofounder Page:
- [ ] Server running on localhost:8000
- [ ] Page loads at /cofounder
- [ ] Instructional box visible (big purple border)
- [ ] Dropdown shows user profiles
- [ ] "Find Matches" button exists
- [ ] Console shows: `"📺 displayMatches called with X matches"` after clicking
- [ ] Match cards appear, instructions disappear

## Next Steps If Still Not Working

### Explain Button:
1. **Hard refresh** the page (Cmd+Shift+R on Mac)
2. **Check** if `result.dimension_explanations` exists in console
3. **Share** the console logs (copy/paste what you see)

### Cofounder Page:
1. **Try** selecting different profiles
2. **Wait** 2-3 seconds after clicking Find Matches
3. **Check** console for: `"❌ Container cf-matches-dynamic not found!"` (would indicate HTML issue)
4. **Share** what the dropdown shows (how many profiles?)

## Technical Details

### Files Modified:
- `api/agent.py` (line 169): Added `dimension_explanations` to response
- `static/js/intake.js` (lines 406-530): `displayDimensionalAnalysis()` with Explain buttons
- `static/js/intake.js` (lines 962-1011): `openExplanation()` / `closeExplanation()` functions
- `templates/intake.html` (lines 215-250): XAI modal HTML
- `templates/cofounder.html` (lines 97-105): Instructional UI
- `static/js/cofounder.js` (line 337): Hide instructions on match load

### What the Console Should Show:

**When submitting idea:**
```javascript
🔍 Dimensional Analysis Data:
- Dimensions: {problem_clarity: 0.72, problem_significance: 0.58, ...}
- Explanations: {problem_clarity: "The user clearly identifies...", ...}
- Explanations keys: ["problem_clarity", "problem_significance", ...]
📊 displayDimensionalAnalysis called
- Explanations parameter: {problem_clarity: "...", ...}
```

**When clicking Explain:**
```javascript
Opening explanation for: problem_clarity
Title: Problem Clarity
Text: The user clearly identifies the problem of...
```

**When finding cofounder matches:**
```javascript
📺 displayMatches called with 11 matches
📺 Container element: FOUND
✅ Rendering 11 match cards
✅ HTML rendered. Container HTML length: 45620
```
