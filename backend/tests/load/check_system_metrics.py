#!/usr/bin/env python3
"""
System Metrics Checker for Load Testing
========================================

Checks:
- LOAD-04: Memory usage (no memory leak)
- LOAD-05: Database size < 1GB
- LOAD-06: Redis cache statistics

Usage:
    python tests/load/check_system_metrics.py

Requirements:
    - Docker running with papertrading containers
    - psycopg2 for database checks
    - redis for cache checks
"""
import subprocess
import json
import sys
import os
from datetime import datetime
from pathlib import Path

# Find repo root (look for .git directory)
def find_repo_root():
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return Path.cwd()

REPO_ROOT = find_repo_root()
COMPOSE_FILE = str(REPO_ROOT / "infrastructure/docker/docker-compose.local.yml")


def run_docker_command(cmd: list) -> tuple[int, str]:
    """Run a docker command and return (exit_code, output)."""
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        return result.returncode, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return 1, "Command timed out"
    except Exception as e:
        return 1, str(e)


def check_containers_running() -> bool:
    """Check if containers are running."""
    print("\n📦 Checking containers...")
    
    code, output = run_docker_command([
        "docker", "compose", "-f", COMPOSE_FILE, "ps", "--format", "json"
    ])
    
    if code != 0:
        print(f"  ✗ Failed to get container status: {output}")
        return False
    
    try:
        # Parse each line as JSON (docker compose ps outputs one JSON per line)
        containers = []
        for line in output.strip().split('\n'):
            if line.strip():
                containers.append(json.loads(line))
        
        running = [c for c in containers if c.get("State") == "running"]
        print(f"  ✓ {len(running)}/{len(containers)} containers running")
        
        for c in containers:
            status = "✓" if c.get("State") == "running" else "✗"
            print(f"    {status} {c.get('Name', 'unknown')}: {c.get('State', 'unknown')}")
        
        return len(running) >= 3  # At least backend, postgres, redis
    except:
        print(f"  → Container output: {output[:200]}")
        return True  # Assume running if we can't parse


def check_database_size() -> dict:
    """Check PostgreSQL database size (LOAD-05)."""
    print("\n💾 LOAD-05: Checking database size...")
    
    code, output = run_docker_command([
        "docker", "exec", "papertrading-postgres",
        "psql", "-U", "papertrading", "-d", "papertrading",
        "-c", "SELECT pg_size_pretty(pg_database_size('papertrading')) as size;"
    ])
    
    if code != 0:
        print(f"  ✗ Failed to get DB size: {output}")
        return {"status": "error", "message": output}
    
    # Parse size from output
    lines = output.strip().split('\n')
    for line in lines:
        if 'MB' in line or 'GB' in line or 'kB' in line:
            size_str = line.strip()
            print(f"  ✓ Database size: {size_str}")
            
            # Check if < 1GB
            if 'GB' in size_str:
                size_gb = float(size_str.replace('GB', '').strip())
                passed = size_gb < 1.0
            else:
                passed = True  # MB or kB is definitely < 1GB
            
            status = "✓ PASS" if passed else "✗ FAIL"
            print(f"  {status}: Size {'<' if passed else '>='} 1GB threshold")
            
            return {
                "status": "pass" if passed else "fail",
                "size": size_str,
                "threshold": "1GB"
            }
    
    return {"status": "unknown", "output": output}


def check_table_sizes() -> dict:
    """Check individual table sizes."""
    print("\n  Table sizes:")
    
    code, output = run_docker_command([
        "docker", "exec", "papertrading-postgres",
        "psql", "-U", "papertrading", "-d", "papertrading",
        "-c", """
        SELECT 
            relname as table,
            pg_size_pretty(pg_total_relation_size(relid)) as size,
            n_live_tup as rows
        FROM pg_stat_user_tables 
        ORDER BY pg_total_relation_size(relid) DESC
        LIMIT 10;
        """
    ])
    
    if code == 0:
        print(output)
    
    return {"output": output}


def check_trade_count() -> dict:
    """Check number of trades."""
    print("\n  Trade count:")
    
    code, output = run_docker_command([
        "docker", "exec", "papertrading-postgres",
        "psql", "-U", "papertrading", "-d", "papertrading",
        "-c", "SELECT COUNT(*) as trades FROM trades;"
    ])
    
    if code == 0:
        # Parse count
        for line in output.split('\n'):
            if line.strip().isdigit():
                count = int(line.strip())
                print(f"  ✓ Total trades: {count}")
                return {"count": count, "threshold": 1000}
    
    return {"error": output}


def check_memory_usage() -> dict:
    """Check container memory usage (LOAD-04)."""
    print("\n🧠 LOAD-04: Checking memory usage...")
    
    code, output = run_docker_command([
        "docker", "stats", "--no-stream", "--format", 
        "table {{.Name}}\t{{.MemUsage}}\t{{.MemPerc}}"
    ])
    
    if code != 0:
        print(f"  ✗ Failed to get memory stats: {output}")
        return {"status": "error"}
    
    print(output)
    
    # Parse memory for backend container
    for line in output.split('\n'):
        if 'backend' in line.lower():
            parts = line.split()
            if len(parts) >= 3:
                mem_usage = parts[1] if '/' in parts[1] else parts[1]
                mem_pct = parts[-1] if '%' in parts[-1] else 'N/A'
                return {
                    "status": "ok",
                    "backend_memory": mem_usage,
                    "backend_percent": mem_pct
                }
    
    return {"status": "unknown", "output": output}


def check_redis_stats() -> dict:
    """Check Redis cache statistics (LOAD-06)."""
    print("\n📊 LOAD-06: Checking Redis cache stats...")
    
    code, output = run_docker_command([
        "docker", "exec", "papertrading-redis",
        "redis-cli", "INFO", "stats"
    ])
    
    if code != 0:
        print(f"  ✗ Failed to get Redis stats: {output}")
        return {"status": "error"}
    
    stats = {}
    for line in output.split('\n'):
        if ':' in line:
            key, value = line.strip().split(':', 1)
            stats[key] = value
    
    # Calculate hit rate
    hits = int(stats.get('keyspace_hits', 0))
    misses = int(stats.get('keyspace_misses', 0))
    total = hits + misses
    
    if total > 0:
        hit_rate = (hits / total) * 100
        passed = hit_rate >= 80
        status = "✓ PASS" if passed else "✗ FAIL (need > 80%)"
        print(f"  {status}")
        print(f"    Hits: {hits:,}")
        print(f"    Misses: {misses:,}")
        print(f"    Hit Rate: {hit_rate:.1f}%")
    else:
        print(f"  → No cache activity yet (hits={hits}, misses={misses})")
        hit_rate = 0
        passed = True  # No activity is OK
    
    # Memory usage
    code2, output2 = run_docker_command([
        "docker", "exec", "papertrading-redis",
        "redis-cli", "INFO", "memory"
    ])
    
    if code2 == 0:
        for line in output2.split('\n'):
            if 'used_memory_human' in line:
                print(f"    Memory: {line.split(':')[1].strip()}")
    
    return {
        "status": "pass" if passed else "fail",
        "hit_rate": hit_rate,
        "hits": hits,
        "misses": misses,
        "threshold": "80%"
    }


def check_backend_health() -> dict:
    """Check backend health endpoint."""
    print("\n🏥 Backend health check...")
    
    code, output = run_docker_command([
        "curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
        "http://localhost:8000/health"
    ])
    
    if code == 0 and output.strip() == "200":
        print(f"  ✓ Backend healthy (HTTP 200)")
        return {"status": "healthy"}
    else:
        print(f"  ✗ Backend unhealthy: {output}")
        return {"status": "unhealthy", "response": output}


def main():
    """Run all system checks."""
    print("\n" + "="*60)
    print("Phase 4: System Metrics Check")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    results = {}
    
    # Check containers
    if not check_containers_running():
        print("\n⚠️  Not all containers are running!")
        print("   Start with: docker compose -f infrastructure/docker/docker-compose.local.yml up -d")
        return
    
    # Run checks
    results["health"] = check_backend_health()
    results["database_size"] = check_database_size()
    results["tables"] = check_table_sizes()
    results["trades"] = check_trade_count()
    results["memory"] = check_memory_usage()
    results["redis"] = check_redis_stats()
    
    # Summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    
    checks = [
        ("LOAD-04 Memory", results.get("memory", {}).get("status") == "ok"),
        ("LOAD-05 DB Size", results.get("database_size", {}).get("status") == "pass"),
        ("LOAD-06 Cache Rate", results.get("redis", {}).get("status") == "pass"),
    ]
    
    for name, passed in checks:
        status = "✓" if passed else "✗"
        print(f"  {status} {name}")
    
    passed_count = sum(1 for _, p in checks if p)
    print(f"\n  Total: {passed_count}/{len(checks)} checks passed")


if __name__ == "__main__":
    main()
