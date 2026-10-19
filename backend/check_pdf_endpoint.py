# Test if the PDF endpoint can be called
import sys
sys.path.insert(0, '.')

try:
    from sonar_routes import router
    print("✓ sonar_routes imported")
    
    # Check if combined-pdf route exists
    routes = [r.path for r in router.routes]
    if '/api/sonar/report/combined-pdf' in routes:
        print("✓ combined-pdf route found")
    else:
        print("❌ combined-pdf route NOT found in routes:")
        print(routes)
    
except Exception as e:
    print(f"❌ Error importing sonar_routes:")
    print(str(e))
    import traceback
    traceback.print_exc()

input("Press Enter...")