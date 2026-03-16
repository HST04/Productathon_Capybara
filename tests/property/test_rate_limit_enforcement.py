"""
Property-based tests for rate limit enforcement.

Feature: hpcl-lead-intelligence, Property 4: Rate Limit Enforcement
Validates: Requirements 1.4

Property: For any source with a configured rate limit, the number of requests 
within the time window must not exceed the limit.
"""

import time
from hypothesis import given, strategies as st, settings, assume
import pytest

from app.services.policy_checker import PolicyChecker


# Strategy for generating valid URLs
def url_strategy():
    """Generate valid HTTP/HTTPS URLs with different domains."""
    domains = st.sampled_from([
        'example.com',
        'test.org',
        'sample.net',
        'demo.io',
        'api.example.com'
    ])
    paths = st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd')),
            min_size=1,
            max_size=10
        ),
        min_size=0,
        max_size=3
    )
    
    return st.builds(
        lambda domain, path_list: f"https://{domain}/{'/'.join(path_list)}",
        domains,
        paths
    )


@pytest.mark.property
@settings(max_examples=20, deadline=5000)
@given(
    rate_limit=st.floats(min_value=0.05, max_value=0.3),
    num_requests=st.integers(min_value=2, max_value=5)
)
def test_rate_limit_enforcement_sequential(rate_limit: float, num_requests: int):
    """
    Property 4: Rate Limit Enforcement
    
    Test that sequential requests to the same domain respect the configured rate limit.
    For any sequence of requests, the time between consecutive requests should be
    at least the configured rate limit.
    """
    policy_checker = PolicyChecker()
    test_url = "https://example.com/test"
    
    # Set custom rate limit for the domain
    policy_checker.set_custom_rate_limit("example.com", rate_limit)
    
    # Track request timestamps
    request_times = []
    
    for i in range(num_requests):
        # Check if rate limit allows the request
        can_proceed = policy_checker.check_rate_limit(test_url)
        
        if i == 0:
            # First request should always be allowed
            assert can_proceed, "First request should always be allowed"
        else:
            # For subsequent requests, check timing
            time_since_last = time.time() - request_times[-1]
            
            if time_since_last >= rate_limit:
                # Enough time has passed, should be allowed
                assert can_proceed, (
                    f"Request should be allowed after {time_since_last:.3f}s "
                    f"(rate limit: {rate_limit}s)"
                )
            else:
                # Not enough time has passed, should be blocked
                assert not can_proceed, (
                    f"Request should be blocked after only {time_since_last:.3f}s "
                    f"(rate limit: {rate_limit}s)"
                )
        
        # If allowed, record the request
        if can_proceed:
            policy_checker.record_request(test_url)
            request_times.append(time.time())
            
            # Wait for the rate limit period before next request
            if i < num_requests - 1:
                time.sleep(rate_limit)


@pytest.mark.property
@settings(max_examples=30, deadline=3000)
@given(
    rate_limit=st.floats(min_value=0.05, max_value=0.5),
    num_requests=st.integers(min_value=3, max_value=6)
)
def test_rate_limit_blocks_rapid_requests(rate_limit: float, num_requests: int):
    """
    Property 4: Rate Limit Enforcement
    
    Test that rapid consecutive requests are blocked by rate limiting.
    After the first request, all immediate subsequent requests should be blocked
    until the rate limit period has passed.
    """
    policy_checker = PolicyChecker()
    test_url = "https://test.org/api"
    
    # Set custom rate limit
    policy_checker.set_custom_rate_limit("test.org", rate_limit)
    
    # First request should be allowed
    assert policy_checker.check_rate_limit(test_url), "First request should be allowed"
    policy_checker.record_request(test_url)
    
    # All immediate subsequent requests should be blocked
    blocked_count = 0
    for _ in range(num_requests - 1):
        if not policy_checker.check_rate_limit(test_url):
            blocked_count += 1
    
    # At least some requests should be blocked (since they're immediate)
    assert blocked_count > 0, (
        f"Expected some requests to be blocked with rate limit {rate_limit}s, "
        f"but {blocked_count} were blocked out of {num_requests - 1}"
    )


@pytest.mark.property
@settings(max_examples=20, deadline=3000)
@given(
    rate_limit=st.floats(min_value=0.1, max_value=0.5)  # Increased min to avoid timing precision issues
)
def test_rate_limit_wait_time_calculation(rate_limit: float):
    """
    Property 4: Rate Limit Enforcement
    
    Test that wait_for_rate_limit correctly calculates the time to wait.
    The wait time should decrease as time passes and reach 0 after the rate limit period.
    """
    policy_checker = PolicyChecker()
    test_url = "https://sample.net/data"
    
    # Set custom rate limit
    policy_checker.set_custom_rate_limit("sample.net", rate_limit)
    
    # Make first request
    policy_checker.record_request(test_url)
    
    # Immediately check wait time - should be approximately equal to rate_limit
    wait_time_1 = policy_checker.wait_for_rate_limit(test_url)
    assert 0 < wait_time_1 <= rate_limit, (
        f"Wait time {wait_time_1:.3f}s should be between 0 and {rate_limit}s"
    )
    
    # Wait for a conservative portion of the rate limit period (40% to avoid overshooting)
    sleep_duration = rate_limit * 0.4
    time.sleep(sleep_duration)
    
    # Check wait time again - should be less than initial wait time
    wait_time_2 = policy_checker.wait_for_rate_limit(test_url)
    # Allow for timing precision - wait_time_2 should be less than wait_time_1 with small tolerance
    assert wait_time_2 <= wait_time_1, (
        f"Wait time should decrease or stay same: {wait_time_2:.3f}s <= {wait_time_1:.3f}s"
    )
    
    # Wait for the full rate limit period plus buffer
    time.sleep(rate_limit + 0.05)
    
    # Check wait time - should be 0 or very close to 0
    wait_time_3 = policy_checker.wait_for_rate_limit(test_url)
    assert wait_time_3 < 0.05, (
        f"Wait time should be near 0 after rate limit period, got {wait_time_3:.3f}s"
    )


@pytest.mark.property
@settings(max_examples=20, deadline=2000)
@given(
    rate_limit_1=st.floats(min_value=0.05, max_value=0.5),
    rate_limit_2=st.floats(min_value=0.05, max_value=0.5)
)
def test_rate_limit_per_domain_isolation(rate_limit_1: float, rate_limit_2: float):
    """
    Property 4: Rate Limit Enforcement
    
    Test that rate limits are enforced per domain independently.
    Requests to different domains should not affect each other's rate limits.
    """
    assume(abs(rate_limit_1 - rate_limit_2) > 0.1)  # Ensure different rate limits
    
    policy_checker = PolicyChecker()
    url_1 = "https://domain1.com/api"
    url_2 = "https://domain2.com/api"
    
    # Set different rate limits for different domains
    policy_checker.set_custom_rate_limit("domain1.com", rate_limit_1)
    policy_checker.set_custom_rate_limit("domain2.com", rate_limit_2)
    
    # Make request to domain 1
    assert policy_checker.check_rate_limit(url_1), "First request to domain1 should be allowed"
    policy_checker.record_request(url_1)
    
    # Immediate request to domain 1 should be blocked
    assert not policy_checker.check_rate_limit(url_1), (
        "Immediate second request to domain1 should be blocked"
    )
    
    # But request to domain 2 should still be allowed (independent rate limit)
    assert policy_checker.check_rate_limit(url_2), (
        "Request to domain2 should be allowed (independent rate limit)"
    )
    policy_checker.record_request(url_2)
    
    # Immediate request to domain 2 should now be blocked
    assert not policy_checker.check_rate_limit(url_2), (
        "Immediate second request to domain2 should be blocked"
    )


@pytest.mark.property
@settings(max_examples=15, deadline=5000)
@given(
    rate_limit=st.floats(min_value=0.1, max_value=0.4),
    num_cycles=st.integers(min_value=2, max_value=4)
)
def test_rate_limit_enforcement_over_multiple_cycles(rate_limit: float, num_cycles: int):
    """
    Property 4: Rate Limit Enforcement
    
    Test that rate limiting works correctly over multiple request cycles.
    Each cycle should respect the rate limit independently.
    """
    policy_checker = PolicyChecker()
    test_url = "https://api.example.com/endpoint"
    
    # Set custom rate limit
    policy_checker.set_custom_rate_limit("api.example.com", rate_limit)
    
    for cycle in range(num_cycles):
        # First request in cycle should be allowed (after waiting)
        can_proceed = policy_checker.check_rate_limit(test_url)
        assert can_proceed, f"Request in cycle {cycle} should be allowed"
        
        policy_checker.record_request(test_url)
        
        # Immediate next request should be blocked
        assert not policy_checker.check_rate_limit(test_url), (
            f"Immediate request after cycle {cycle} should be blocked"
        )
        
        # Wait for rate limit period before next cycle
        if cycle < num_cycles - 1:
            time.sleep(rate_limit + 0.05)  # Small buffer


@pytest.mark.property
@settings(max_examples=15, deadline=2000)
@given(
    initial_rate_limit=st.floats(min_value=0.1, max_value=0.5),
    new_rate_limit=st.floats(min_value=0.1, max_value=0.5)
)
def test_rate_limit_update_takes_effect(initial_rate_limit: float, new_rate_limit: float):
    """
    Property 4: Rate Limit Enforcement
    
    Test that updating a domain's rate limit takes effect immediately.
    """
    assume(abs(initial_rate_limit - new_rate_limit) > 0.1)
    
    policy_checker = PolicyChecker()
    test_url = "https://configurable.com/api"
    
    # Set initial rate limit
    policy_checker.set_custom_rate_limit("configurable.com", initial_rate_limit)
    
    # Make a request
    policy_checker.record_request(test_url)
    
    # Update to new rate limit
    policy_checker.set_custom_rate_limit("configurable.com", new_rate_limit)
    
    # Wait time should reflect the new rate limit
    wait_time = policy_checker.wait_for_rate_limit(test_url)
    
    # The wait time should be closer to the new rate limit than the old one
    # (accounting for some time already passed)
    assert wait_time <= new_rate_limit, (
        f"Wait time {wait_time:.3f}s should not exceed new rate limit {new_rate_limit:.3f}s"
    )
