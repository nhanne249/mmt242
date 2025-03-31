import asyncio
from Server import PeerTracker
from Client import PeerClient
from colorama import Fore, Style
from multiprocessing.pool import ThreadPool
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread

async def run_tracker():
    """Run the tracker server."""
    tracker = PeerTracker(port=1108)
    await tracker.start()

async def run_peer(peer_ip, peer_port, peer_name, files, tracker_ip='127.0.0.1', tracker_port=1108, request_files=None):
    """Run a peer client that registers with the tracker, holds files, and optionally requests files."""
    client = PeerClient(tracker_ip, tracker_port, peer_port, files, peer_name=peer_name)

    print(f"{Fore.YELLOW}[{peer_name}]{Style.RESET_ALL} Starting and connecting to tracker...")
    await client.connect_to_tracker()

    if request_files:
        await asyncio.sleep(3)  # Delay to simulate idle time
        print(f"{Fore.YELLOW}[{peer_name}]{Style.RESET_ALL} Asking tracker for peers to request files from...")
        receive = await client.get_n_file_idle_peers(request_files)
        print(f'{Fore.YELLOW}[MAIN]{Style.RESET_ALL} Gathering...')
        available_peers = receive.get('file_peer', [])
        file_sizes = receive.get('file_sizes', [])
        
        async def task_runner(file_name, peer):
            print(f'{Fore.YELLOW}[MAIN]{Style.RESET_ALL} Available: {file_name}: {peer}')
            task = client.request_file(peer, file_name, file_sizes[file_name]['file_size'])
            await task
        
        await asyncio.gather(*[asyncio.create_task(task_runner(file_name, peer)) for file_name, peer in available_peers])

async def run_peer_thread(peer_ip, peer_port, peer_name, files, tracker_ip='127.0.0.1', tracker_port=1108, request_files=None):
    """Run a peer client that registers with the tracker, holds files, and optionally requests files."""
    client = PeerClient(tracker_ip, tracker_port, peer_port, files, peer_name=peer_name)

    print(f"{Fore.YELLOW}[{peer_name}]{Style.RESET_ALL} Starting and connecting to tracker...")
    await client.connect_to_tracker()

    if request_files:
        await asyncio.sleep(3)  # Delay to simulate idle time
        print(f"{Fore.YELLOW}[{peer_name}]{Style.RESET_ALL} Asking tracker for peers to request files from...")
        receive = await client.get_n_file_idle_peers(request_files)
        print(f'{Fore.YELLOW}[MAIN]{Style.RESET_ALL} Gathering...')
        available_peers = receive.get('file_peer', [])
        file_sizes = receive.get('file_sizes', [])
        
        async def task_runner(file_name, peer):
            print(f'{Fore.YELLOW}[MAIN]{Style.RESET_ALL} Available: {file_name}: {peer}')
            task = client.request_file(peer, file_name, file_sizes[file_name]['file_size'])
            await task
        
        thread_list = [Thread(target=asyncio.run, args=(task_runner(file_name, peer),)) for file_name, peer in available_peers]
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()

async def main():
    """Main function to set up the tracker and peers."""
    tracker_task = asyncio.create_task(run_tracker())

    # Create peers with files
    peer_a_files = ['fileA1.txt', 'fileA2.txt', 'fileA3.txt']
    peer_b_files = ['fileB1.txt', 'fileB2.txt']
    peer_c_files = []  # Peer C does not have any files
    peer_d_files = ['fileD1.txt', 'fileD2.txt']

    # Create peer tasks
    peer_a_task = asyncio.create_task(run_peer('127.0.0.1', 1109, 'PEER A', peer_a_files, tracker_ip='127.0.0.1'))
    peer_b_task = asyncio.create_task(run_peer('127.0.0.1', 1110, 'PEER B', peer_b_files))
    peer_c_task = asyncio.create_task(run_peer('127.0.0.1', 1111, 'PEER C', peer_c_files, request_files=['fileA1.txt', 'fileB1.txt', 'fileD1.txt']))
    peer_d_task = asyncio.create_task(run_peer('127.0.0.1', 1112, 'PEER D', peer_d_files, request_files=['fileA1.txt', 'fileB1.txt']))

    await asyncio.gather(tracker_task, peer_a_task, peer_b_task, peer_c_task, peer_d_task)

def main_thread():
    """Main function to set up the tracker and peers."""
    tracker_task = run_tracker()
    # Create peers with files
    peer_a_files = ['fileA1.txt', 'fileA2.txt', 'fileA3.txt']
    peer_b_files = ['fileB1.txt', 'fileB2.txt']
    peer_c_files = []  # Peer C does not have any files
    peer_d_files = ['fileD1.txt', 'fileD2.txt']

    # Create peer tasks
    peer_a_task = run_peer('127.0.0.1', 1109, 'PEER A', peer_a_files)
    peer_b_task = run_peer('127.0.0.1', 1110, 'PEER B', peer_b_files)
    peer_c_task = run_peer('127.0.0.1', 1111, 'PEER C', peer_c_files, request_files=['fileA1.txt', 'fileB1.txt', 'fileD1.txt'])
    peer_d_task = run_peer('127.0.0.1', 1112, 'PEER D', peer_d_files, request_files=['fileA1.txt', 'fileB1.txt'])
    # Run the tracker and peers parallelly
    with ThreadPoolExecutor(max_workers=5) as executor:
        executor.submit(asyncio.run, tracker_task)
        executor.submit(asyncio.run, peer_a_task)
        executor.submit(asyncio.run, peer_b_task)
        executor.submit(asyncio.run, peer_c_task)
        executor.submit(asyncio.run, peer_d_task)
        futures = [tracker_task, peer_a_task, peer_b_task, peer_c_task, peer_d_task]
        # Wait for all tasks to complete
        try:
            for future in as_completed(futures):
                result = future.result()  # This will raise if there was an exception in the task
                print(result)
        except Exception as e:
            print(f"Exception caught: {e}")
            # Shutdown the executor and cancel pending tasks
            executor.shutdown(wait=False, cancel_futures=True)


# Run the main function
if __name__ == '__main__':
    try:
        main_thread()
    except KeyboardInterrupt:
        pass
    finally:
        print(f"{Fore.RED}[MAIN]{Style.RESET_ALL} Goodbye for now!")
