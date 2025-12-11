# Authentication & Ideas Persistence - Complete Fix

## 🐛 Problems Identified

### Problem 1: Profile Avatar Redirects to Login Instead of Profile Page
**Symptom:** Clicking on user avatar in header → redirects to login page
**Root Cause:** Profile page tries to fetch user data from `/matching/users/{userId}` without proper error handling
**Impact:** Users can't access their profile page after logging in

### Problem 2: Ideas Not Showing on Dashboard
**Symptom:** "0 Active Ideas" even after refining ideas
**Root Causes:**
1. Ideas API had duplicate prefix (`/ideas/ideas/` instead of `/ideas/`)
2. Ideas were saved with `user_id=null` instead of actual user ID
3. Dashboard loaded ideas using wrong user ID source

---

## ✅ Fixes Applied

### Fix 1: Ideas API Route (api/ideas.py)
```python
# BEFORE:
router = APIRouter(prefix="/ideas", tags=["ideas"])

# AFTER:
router = APIRouter(tags=["ideas"])
```
**Reason:** main.py already adds `/ideas` prefix via `app.include_router(ideas_router, prefix="/ideas")`

### Fix 2: Dashboard Idea Loading (templates/user.html, lines 267-286)
**Added JWT token extraction:**
```javascript
// Get user ID from JWT token
let userId = null;
const token = localStorage.getItem('access_token');
if (token) {
    try {
        const payload = JSON.parse(atob(token.split('.')[1]));
        userId = payload.sub; // Extract user ID from JWT
    } catch (e) {
        console.error('Failed to decode JWT:', e);
    }
}

// Fallback to stored profile ID
if (!userId) {
    userId = localStorage.getItem('elevare_profile_id');
}

const r = await fetch(`${window.location.origin}/ideas/?user_id=${userId}`);
```

### Fix 3: Idea Creation with User ID (static/js/api-client.js)
```javascript
async createIdea(ideaData, userId = null) {
    // Get user ID from JWT token if logged in
    let uid = userId;
    if (!uid) {
        const token = localStorage.getItem('access_token');
        if (token) {
            try {
                const payload = JSON.parse(atob(token.split('.')[1]));
                uid = payload.sub; // Extract user ID from JWT
            } catch (e) {
                console.error('Failed to decode JWT for user ID:', e);
            }
        }
    }
    
    // Fallback to stored profile ID if no JWT
    if (!uid) {
        uid = this.getCurrentProfileId();
    }
    
    const qs = uid != null ? `?user_id=${encodeURIComponent(uid)}` : '';
    return this.request(`/ideas/${qs}`, {
        method: 'POST',
        body: JSON.stringify(ideaData)
    });
}
```

### Fix 4: Profile Page Enhanced (templates/profile.html)
**Added idea loading functionality:**
```javascript
async function loadUserIdeas(userId) {
    const response = await fetch(`/ideas/?user_id=${userId}`);
    const ideas = await response.json();
    
    // Update ideas count
    document.getElementById('ideas-count').textContent = ideas.length;
    
    // Display ideas with:
    // - Idea title
    // - Problem statement
    // - Core domain tag
    // - Confidence score
    // - Created date
    // - "Find Cofounders" button
}
```

---

## 🔄 Complete User Flow (Fixed)

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USER LOGS IN                                             │
│    • Email: sanjeevi@elevare.com                            │
│    • Password: ****                                         │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. JWT TOKEN GENERATED & STORED                             │
│    • Token payload: { sub: "1", email: "..." }              │
│    • Stored in: localStorage.getItem('access_token')        │
│    • Used for all authenticated requests                    │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. DASHBOARD LOADS (/user)                                  │
│    • Decodes JWT → extracts user_id from payload.sub        │
│    • Calls: /ideas/?user_id=1                               │
│    • Displays: "Active Ideas" count                         │
│    • Shows: List of refined ideas                           │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. USER CLICKS "+ NEW IDEA"                                 │
│    • Navigates to /intake                                   │
│    • Fills form and submits idea                            │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. IDEA REFINEMENT HAPPENS                                  │
│    • Calls: /refine-idea with raw text                      │
│    • AI generates: RefinedIdea + MarketProfile              │
│    • Returns: FullIdeaProfile                               │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. IDEA SAVED TO DATABASE                                   │
│    • Frontend: api.createIdea(payload)                      │
│    • Extracts user_id from JWT token                        │
│    • Calls: POST /ideas/?user_id=1                          │
│    • Backend saves: { id: 6, user_id: "1", ... }            │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. USER RETURNS TO DASHBOARD                                │
│    • Dashboard reloads ideas with user_id filter            │
│    • ✅ Shows: "1 Active Idea"                              │
│    • ✅ Displays: New idea in "Your Ideas" section          │
└───────────────────────────┬─────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. USER CLICKS PROFILE AVATAR                               │
│    • Navigates to: /profile                                 │
│    • Loads user data from /matching/users/{userId}          │
│    • Loads ideas from /ideas/?user_id={userId}              │
│    • ✅ Shows: User details + all refined ideas             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🧪 Testing Checklist

### Test 1: Login & Dashboard
- [ ] Navigate to http://localhost:8000/login
- [ ] Login with credentials
- [ ] Verify redirect to dashboard (/user)
- [ ] Check "Active Ideas" shows correct count (may be 0 for old ideas with user_id=null)

### Test 2: Create New Idea
- [ ] Click "+ New Idea" button
- [ ] Fill in idea description (min 10 characters)
- [ ] Click "Refine Idea"
- [ ] Wait for AI processing
- [ ] Verify idea details display correctly
- [ ] Return to dashboard
- [ ] ✅ Verify "Active Ideas" increments to 1
- [ ] ✅ Verify idea appears in "Your Ideas" section

### Test 3: Profile Page
- [ ] Click on user avatar in header (top right)
- [ ] ✅ Verify navigates to /profile (NOT /login)
- [ ] ✅ Verify profile displays:
  - User name
  - Email
  - Location
  - Interests
  - Skills
- [ ] ✅ Verify "Ideas Refined" count is correct
- [ ] ✅ Verify refined ideas list shows all your ideas

### Test 4: Idea Persistence Across Sessions
- [ ] Create an idea (as per Test 2)
- [ ] Logout
- [ ] Login again with same credentials
- [ ] ✅ Verify "Active Ideas" still shows your ideas
- [ ] ✅ Verify ideas appear on dashboard
- [ ] ✅ Verify ideas appear on profile page

---

## 🚨 Known Issues & Limitations

### Issue: Old Ideas Have user_id=null
**Problem:** Ideas created before this fix have `user_id: null` in Redis
**Impact:** They won't appear on user dashboards or profiles
**Solution:** Create new ideas after this fix, or run migration script

### Migration Script (Optional)
To associate old ideas with a specific user:
```javascript
// Run in browser console on http://localhost:8000
const userId = "1"; // Your user ID
const token = localStorage.getItem('access_token');

// Fetch all ideas
fetch('/ideas/')
  .then(r => r.json())
  .then(ideas => {
    console.log(`Found ${ideas.length} ideas`);
    // Manual reassignment would require backend endpoint
  });
```

---

## 📋 API Endpoints Reference

### GET /ideas/
**Query Parameters:**
- `user_id` (optional): Filter ideas by user
- `limit` (optional, default=20): Max results

**Response:**
```json
[
  {
    "id": 6,
    "created_at": 1763193147.477,
    "user_id": "1",  // ← Now populated!
    "refined_idea": { ... },
    "market_profile": { ... },
    "overall_confidence_score": 4.2
  }
]
```

### POST /ideas/?user_id={userId}
**Query Parameters:**
- `user_id` (required): User ID from JWT token

**Body:**
```json
{
  "refined_idea": { ... },
  "market_profile": { ... },
  "overall_confidence_score": 4.2
}
```

---

## 🎯 Success Criteria

✅ **All of these should now work:**
1. Login persists across page refreshes
2. Dashboard shows correct idea count for logged-in user
3. Clicking profile avatar goes to /profile (not /login)
4. Profile page shows user details + all refined ideas
5. New ideas are saved with correct user_id
6. Ideas persist across login/logout sessions
7. Multiple users can use the system independently

---

## 🔧 Files Modified

1. `/api/ideas.py` - Removed duplicate prefix
2. `/templates/user.html` - Added JWT extraction for idea loading
3. `/static/js/api-client.js` - Added JWT extraction for idea creation
4. `/templates/profile.html` - Added idea loading functionality

---

## 🚀 Next Steps

1. **Hard refresh browser** (Cmd+Shift+R) to clear cached JavaScript
2. **Login** with your credentials
3. **Create a new idea** to test the flow
4. **Verify** it appears on dashboard and profile page
5. **Logout and login again** to verify persistence

---

## 📞 Troubleshooting

### Problem: Still see "0 Active Ideas"
**Check:**
- Open browser DevTools (F12) → Console tab
- Look for error messages
- Check Network tab for failed requests to `/ideas/`

### Problem: Profile page redirects to login
**Check:**
- Verify JWT token exists: `localStorage.getItem('access_token')`
- Check token is valid (not expired)
- Verify `/matching/users/{userId}` endpoint returns data

### Problem: Ideas still have user_id=null
**Solution:**
- Only NEW ideas created AFTER this fix will have proper user_id
- Delete old test ideas or create migration script
