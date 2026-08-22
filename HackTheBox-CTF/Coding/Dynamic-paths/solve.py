
from pwn import *

# Server target
HOST = "IP" # Your IP
PORT = 12345 # Your port

def solve_grid(rows, cols, values):
    grid = [values[k * cols : (k + 1) * cols] for k in range(rows)]
    dp = [[0] * cols for _ in range(rows)]
    
    dp[0][0] = grid[0][0]
    
    # Fill first row
    for j in range(1, cols):
        dp[0][j] = dp[0][j - 1] + grid[0][j]
        
    # Fill first column
    for i in range(1, rows):
        dp[i][0] = dp[i - 1][0] + grid[i][0]
        
    # Fill remaining DP table
    for i in range(1, rows):
        for j in range(1, cols):
            dp[i][j] = grid[i][j] + min(dp[i - 1][j], dp[i][j - 1])
            
    return dp[rows - 1][cols - 1]

def main():
    r = remote(HOST, PORT)

    for t in range(1, 101):
        r.recvuntil(f"Test {t}/100\n".encode())
        
        # Read dimensions
        dim_line = r.recvline().decode().strip()
        while not dim_line:
            dim_line = r.recvline().decode().strip()
        rows, cols = map(int, dim_line.split())
        
        # Read grid numbers
        values_line = r.recvline().decode().strip()
        values = list(map(int, values_line.split()))
        
        # Calculate minimum sum
        ans = solve_grid(rows, cols, values)
        print(f"[*] Test {t}/100 ({rows}x{cols}) -> Minimum Sum: {ans}")
        
        # Send result back to server
        r.sendline(str(ans).encode())

    # Receive final flag
    print("\n[+] Flag:", r.recvall().decode())

if __name__ == "__main__":
    main()
