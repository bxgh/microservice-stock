
import akshare as ak

def list_functions():
    attributes = dir(ak)
    keywords = ['issue', 'ipo', 'industry', 'shenwan', 'sector', 'sw_', 'index_classify']
    found = []
    for attr in attributes:
        for kw in keywords:
            if kw in attr.lower():
                found.append(attr)
                break
    
    print("Found potential functions:")
    for f in sorted(found):
        print(f)

if __name__ == "__main__":
    list_functions()
