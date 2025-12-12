# Quick Action Plan

## Immediate Actions (This Week)

### 1. Security Fixes (2-3 hours)
- [ ] Remove hardcoded API key from `app/llm.py`
- [ ] Move API key to environment variable
- [ ] Add environment variable validation
- [ ] Disable dev mode authentication in production

### 2. Code Consolidation (3-4 hours)
- [ ] Decide which app file is production (`app.py` vs `app_new.py`)
- [ ] Remove or archive the unused one
- [ ] Fix hardcoded metrics in UI (lines 264-277 in app.py, 393-405 in app_new.py)
- [ ] Use calculated values from `create_summary_metrics()`

### 3. Configuration Management (2 hours)
- [ ] Create `app/config.py` with all constants
- [ ] Move all hardcoded values to config
- [ ] Document required environment variables

## Short-term Actions (Next 2 Weeks)

### 4. Database Integration (1 week)
- [ ] Complete database integration
- [ ] Remove Excel file dependency
- [ ] Implement proper data loading from database
- [ ] Add database connection pooling

### 5. Error Handling (3-4 days)
- [ ] Add try-except blocks to all functions
- [ ] Implement retry logic for external APIs
- [ ] Add graceful degradation
- [ ] Improve error messages

### 6. Basic Testing (3-4 days)
- [ ] Set up pytest
- [ ] Write unit tests for core functions
- [ ] Add integration tests for database
- [ ] Set up CI/CD pipeline

## Medium-term Actions (Next Month)

### 7. Code Quality
- [ ] Add type hints
- [ ] Remove unused imports
- [ ] Delete dead code
- [ ] Standardize code style

### 8. Documentation
- [ ] Complete docstrings
- [ ] Update README
- [ ] Document API endpoints
- [ ] Create architecture diagram

### 9. LLM Integration Consolidation
- [ ] Choose single LLM implementation
- [ ] Remove unused implementations
- [ ] Document fallback strategy

## Quick Wins (Can Do Today)

1. **Fix hardcoded metrics** - 15 minutes
2. **Remove unused imports** - 30 minutes  
3. **Add config.py** - 1 hour
4. **Move API key to env** - 30 minutes

Total: ~2.5 hours for immediate improvements

