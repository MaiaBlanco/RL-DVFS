sudo apt-get update
sudo apt-get install linux-headers-3.10.105-141 build-essential
cd /usr/src
git clone --depth 1 https://github.com/hardkernel/linux.git -b odroidxu3-3.10.y odroidxu3-3.10.y
cd -
sudo ln -s /usr/src/linux-headers-3.13.105-141/ /lib/modules/3.10.105-141/build
sudo ln -s /usr/src/odroidxu3-3.10.y/arch/arm/mach-exynos/include/mach/ /usr/src/linux-headers-3.10.105-141/include/mach
