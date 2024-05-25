import numpy as np


#arr = np.load(r"C:\Users\arthu\Documents\GitHub\Minecraft-2\365875387\chunks_renderables_0_10.npy")
arr = np.load(r"C:\Users\arthu\Documents\GitHub\Minecraft-2\mwahohooasa_27\chunks_7_28.npy")

"""print(arr.shape)
for x in range(arr.shape[0]):
    for y in range(arr.shape[1]):
        for z in range(arr.shape[2]):
            if arr[x, y, z] == 13:
                print(x, y, z)
"""
print(arr.tolist())