$begin 'Profile'
	$begin 'ProfileGroup'
		MajorVer=2025
		MinorVer=2
		Name='Solution Process'
		$begin 'StartInfo'
			I(1, 'Start Time', '06/14/2026 08:51:58')
			I(1, 'Host', 'harrypc')
			I(1, 'Processor', '32')
			I(1, 'OS', 'Linux 7.0.0-22-generic')
			I(1, 'Product', 'HFSS Version 2025.2.0')
		$end 'StartInfo'
		$begin 'TotalInfo'
			I(1, 'Elapsed Time', '00:46:30')
			I(1, 'ComEngine Memory', '128 M')
		$end 'TotalInfo'
		GroupOptions=8
		TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'Executing From\', \'/opt/ansys_inc/v252/AnsysEM/HFSSCOMENGINE.exe\')', false, true)
		$begin 'ProfileGroup'
			MajorVer=2025
			MinorVer=2
			Name='HPC'
			$begin 'StartInfo'
				I(1, 'Type', 'Auto')
				I(1, 'MPI Vendor', 'Intel')
				I(1, 'MPI Version', '2021')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(0, ' ')
			$end 'TotalInfo'
			GroupOptions=0
			TaskDataOptions(Memory=8)
			ProfileItem('Machine', 0, 0, 0, 0, 0, 'I(5, 1, \'Name\', \'harrypc\', 1, \'Memory\', \'110 GB\', 3, \'RAM Limit\', 90, \'%f%%\', 2, \'Cores\', 4, false, 1, \'Free Disk Space\', \'324 GB\')', false, true)
		$end 'ProfileGroup'
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'Allow off core\', \'True\')', false, true)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'Solution Basis Order\', \'0\')', false, true)
		ProfileItem('Design Validation', 0, 0, 0, 0, 0, 'I(1, 0, \'Elapsed time : 00:00:00 , HFSS ComEngine Memory : 121 M\')', false, true)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Perform full validations with standard port validations\')', false, true)
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
		$begin 'ProfileGroup'
			MajorVer=2025
			MinorVer=2
			Name='Initial Meshing'
			$begin 'StartInfo'
				I(1, 'Time', '06/14/2026 08:51:58')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(1, 'Elapsed Time', '00:00:16')
			$end 'TotalInfo'
			GroupOptions=4
			TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
			ProfileItem('Stitch', 0, 0, 0, 0, 67672, 'I(1, 2, \'Triangles\', 1082, false)', true, true)
			ProfileItem('Mesh', 2, 0, 2, 0, 78848, 'I(2, 1, \'Type\', \'Classic\', 2, \'Tetrahedra\', 5201, false)', true, true)
			ProfileItem('Post', 1, 0, 0, 0, 85700, 'I(1, 2, \'Tetrahedra\', 6839, false)', true, true)
			ProfileItem('Manual Refine', 6, 0, 6, 0, 125156, 'I(2, 2, \'Tetrahedra\', 56865, false, 0, \'Length1\')', true, true)
			ProfileItem('Simulation Setup', 0, 0, 0, 0, 260528, 'I(2, 2, \'Tetrahedra\', 56865, false, 1, \'Disk\', \'0 Bytes\')', true, true)
			ProfileItem('Port Adapt', 0, 0, 0, 0, 273728, 'I(2, 2, \'Tetrahedra\', 56865, false, 1, \'Disk\', \'5.11 KB\')', true, true)
			ProfileItem('Port Refine', 2, 0, 2, 0, 83460, 'I(1, 2, \'Tetrahedra\', 57230, false)', true, true)
		$end 'ProfileGroup'
		$begin 'ProfileGroup'
			MajorVer=2025
			MinorVer=2
			Name='Adaptive Meshing'
			$begin 'StartInfo'
				I(1, 'Time', '06/14/2026 08:52:14')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(1, 'Elapsed Time', '00:15:35')
			$end 'TotalInfo'
			GroupOptions=4
			TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 1'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 0, 0, 0, 0, 265772, 'I(2, 2, \'Tetrahedra\', 57230, false, 1, \'Disk\', \'25.4 KB\')', true, true)
				ProfileItem('Matrix Assembly', 0, 0, 1, 0, 309204, 'I(3, 2, \'Tetrahedra\', 57230, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'63.3 KB\')', true, true)
				ProfileItem('Matrix Solve', 0, 0, 2, 0, 555832, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 67207, false, 3, \'Matrix bandwidth\', 8.64863, \'%5.1f\', 1, \'Disk\', \'266 KB\')', true, true)
				ProfileItem('Field Recovery', 0, 0, 1, 0, 555832, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'6.83 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 130636, 'I(1, 0, \'Adaptive Pass 1\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427136')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.025122\', 1, \'Fbscputimesec\', \'0.075367\', 1, \'Fbsmemorytotalkb\', \'255532.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'0.218937\', 1, \'Factorizationmentotalkb\', \'162783.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'6670\', 1, \'Factornnz\', \'7390083\', 1, \'Factorestflops\', \'3798859359\', 1, \'Fbsestflops\', \'23869828\', 1, \'Rootfactestflops\', \'43959279\', 1, \'Rootfbsestflops\', \'129540\', 1, \'Analysistimesec\', \'0.317726\', 1, \'Analysismemkb\', \'76096.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'555832\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'67207\', 1, \'Matrixbw\', \'8.653760\', 1, \'Matrixnnz\', \'581593\', 1, \'Rootdim\', \'509\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'125649001956507648.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 2'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 3, 0, 3, 0, 119380, 'I(1, 2, \'Tetrahedra\', 74402, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 0, 0, 0, 0, 304484, 'I(2, 2, \'Tetrahedra\', 74402, false, 1, \'Disk\', \'27.1 KB\')', true, true)
				ProfileItem('Matrix Assembly', 1, 0, 2, 0, 357536, 'I(3, 2, \'Tetrahedra\', 74402, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'225 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 1, 0, 4, 0, 749460, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 87095, false, 3, \'Matrix bandwidth\', 8.67517, \'%5.1f\', 1, \'Disk\', \'342 KB\')', true, true)
				ProfileItem('Field Recovery', 0, 0, 2, 0, 749460, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'2.93 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 130640, 'I(1, 0, \'Adaptive Pass 2\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427148')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.038465\', 1, \'Fbscputimesec\', \'0.115396\', 1, \'Fbsmemorytotalkb\', \'404956.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'0.563306\', 1, \'Factorizationmentotalkb\', \'319930.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'8718\', 1, \'Factornnz\', \'13997917\', 1, \'Factorestflops\', \'12491374133\', 1, \'Fbsestflops\', \'47864374\', 1, \'Rootfactestflops\', \'100706146\', 1, \'Rootfbsestflops\', \'225120\', 1, \'Analysistimesec\', \'0.479627\', 1, \'Analysismemkb\', \'95032.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'749460\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'87095\', 1, \'Matrixbw\', \'8.679740\', 1, \'Matrixnnz\', \'755962\', 1, \'Rootdim\', \'671\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'138639001694240768.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.863795, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 3'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 3, 0, 3, 0, 129520, 'I(1, 2, \'Tetrahedra\', 89278, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 0, 0, 0, 0, 337236, 'I(2, 2, \'Tetrahedra\', 89278, false, 1, \'Disk\', \'35.6 KB\')', true, true)
				ProfileItem('Matrix Assembly', 1, 0, 2, 0, 400392, 'I(3, 2, \'Tetrahedra\', 89278, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'150 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 1, 0, 5, 0, 1014696, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 104443, false, 3, \'Matrix bandwidth\', 8.68172, \'%5.1f\', 1, \'Disk\', \'410 KB\')', true, true)
				ProfileItem('Field Recovery', 0, 0, 2, 0, 1014696, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'2.92 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134208, 'I(1, 0, \'Adaptive Pass 3\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427158')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.039901\', 1, \'Fbscputimesec\', \'0.119705\', 1, \'Fbsmemorytotalkb\', \'632100.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'0.751533\', 1, \'Factorizationmentotalkb\', \'435339.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'10456\', 1, \'Factornnz\', \'19858856\', 1, \'Factorestflops\', \'21965953811\', 1, \'Fbsestflops\', \'69256295\', 1, \'Rootfactestflops\', \'104812939\', 1, \'Rootfbsestflops\', \'231200\', 1, \'Analysistimesec\', \'0.536887\', 1, \'Analysismemkb\', \'107688.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'1014696\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'104443\', 1, \'Matrixbw\', \'8.685860\', 1, \'Matrixnnz\', \'907177\', 1, \'Rootdim\', \'680\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'123961998932180992.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.228087, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 4'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 2, 0, 3, 0, 126008, 'I(1, 2, \'Tetrahedra\', 96874, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 1, 0, 1, 0, 352960, 'I(2, 2, \'Tetrahedra\', 96874, false, 1, \'Disk\', \'41.7 KB\')', true, true)
				ProfileItem('Matrix Assembly', 1, 0, 2, 0, 419860, 'I(3, 2, \'Tetrahedra\', 96874, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 1, 0, 6, 0, 1126956, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 113295, false, 3, \'Matrix bandwidth\', 8.6849, \'%5.1f\', 1, \'Disk\', \'444 KB\')', true, true)
				ProfileItem('Field Recovery', 0, 0, 3, 0, 1126956, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'2.28 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134208, 'I(1, 0, \'Adaptive Pass 4\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427170')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.069082\', 1, \'Fbscputimesec\', \'0.207246\', 1, \'Fbsmemorytotalkb\', \'725492.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'0.897462\', 1, \'Factorizationmentotalkb\', \'495692.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'11301\', 1, \'Factornnz\', \'22820470\', 1, \'Factorestflops\', \'26872282325\', 1, \'Fbsestflops\', \'80035775\', 1, \'Rootfactestflops\', \'70216454\', 1, \'Rootfbsestflops\', \'177012\', 1, \'Analysistimesec\', \'0.564538\', 1, \'Analysismemkb\', \'126400.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'1126956\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'113295\', 1, \'Matrixbw\', \'8.688750\', 1, \'Matrixnnz\', \'984392\', 1, \'Rootdim\', \'595\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'139462003327500288.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.0301966, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 5'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 3, 0, 3, 0, 140280, 'I(1, 2, \'Tetrahedra\', 108913, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 1, 0, 1, 0, 377560, 'I(2, 2, \'Tetrahedra\', 108913, false, 1, \'Disk\', \'47.5 KB\')', true, true)
				ProfileItem('Matrix Assembly', 1, 0, 2, 0, 452436, 'I(3, 2, \'Tetrahedra\', 108913, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'75 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 2, 0, 7, 0, 1238528, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 127338, false, 3, \'Matrix bandwidth\', 8.68791, \'%5.1f\', 1, \'Disk\', \'499 KB\')', true, true)
				ProfileItem('Field Recovery', 0, 0, 3, 0, 1238528, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'2.94 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134376, 'I(1, 0, \'Adaptive Pass 5\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427183')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.062408\', 1, \'Fbscputimesec\', \'0.187226\', 1, \'Fbsmemorytotalkb\', \'807652.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'1.193260\', 1, \'Factorizationmentotalkb\', \'613674.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'12703\', 1, \'Factornnz\', \'28163238\', 1, \'Factorestflops\', \'37763364129\', 1, \'Fbsestflops\', \'101541727\', 1, \'Rootfactestflops\', \'57604060\', 1, \'Rootfbsestflops\', \'155124\', 1, \'Analysistimesec\', \'0.798880\', 1, \'Analysismemkb\', \'152576.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'1238528\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'127338\', 1, \'Matrixbw\', \'8.691580\', 1, \'Matrixnnz\', \'1106768\', 1, \'Rootdim\', \'557\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'127806999684448256.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.0101473, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 6'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 5, 0, 5, 0, 169444, 'I(1, 2, \'Tetrahedra\', 131943, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 1, 0, 1, 0, 429912, 'I(2, 2, \'Tetrahedra\', 131943, false, 1, \'Disk\', \'53.4 KB\')', true, true)
				ProfileItem('Matrix Assembly', 1, 0, 3, 0, 519344, 'I(3, 2, \'Tetrahedra\', 131943, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 3, 0, 11, 0, 1592652, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 154202, false, 3, \'Matrix bandwidth\', 8.69259, \'%5.1f\', 1, \'Disk\', \'604 KB\')', true, true)
				ProfileItem('Field Recovery', 1, 0, 4, 0, 1592652, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.48 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134376, 'I(1, 0, \'Adaptive Pass 6\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427199')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.078019\', 1, \'Fbscputimesec\', \'0.234056\', 1, \'Fbsmemorytotalkb\', \'1081320.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'1.931770\', 1, \'Factorizationmentotalkb\', \'910693.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'15366\', 1, \'Factornnz\', \'40395216\', 1, \'Factorestflops\', \'67710622748\', 1, \'Fbsestflops\', \'155702145\', 1, \'Rootfactestflops\', \'91543161\', 1, \'Rootfbsestflops\', \'211250\', 1, \'Analysistimesec\', \'0.956371\', 1, \'Analysismemkb\', \'164112.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'1592652\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'154202\', 1, \'Matrixbw\', \'8.695720\', 1, \'Matrixnnz\', \'1340898\', 1, \'Rootdim\', \'650\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'126927003835170816.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.0072001, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 7'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 6, 0, 6, 0, 194232, 'I(1, 2, \'Tetrahedra\', 157823, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 2, 0, 2, 0, 485988, 'I(2, 2, \'Tetrahedra\', 157823, false, 1, \'Disk\', \'61.8 KB\')', true, true)
				ProfileItem('Matrix Assembly', 2, 0, 4, 0, 590068, 'I(3, 2, \'Tetrahedra\', 157823, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'150 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 4, 0, 15, 0, 1895216, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 184450, false, 3, \'Matrix bandwidth\', 8.69352, \'%5.1f\', 1, \'Disk\', \'722 KB\')', true, true)
				ProfileItem('Field Recovery', 1, 0, 4, 0, 1895216, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'5.22 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134376, 'I(1, 0, \'Adaptive Pass 7\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427217')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.128173\', 1, \'Fbscputimesec\', \'0.384519\', 1, \'Fbsmemorytotalkb\', \'1338200.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'2.941130\', 1, \'Factorizationmentotalkb\', \'1199850.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'18416\', 1, \'Factornnz\', \'53586020\', 1, \'Factorestflops\', \'103630559980\', 1, \'Fbsestflops\', \'214676488\', 1, \'Rootfactestflops\', \'130207589\', 1, \'Rootfbsestflops\', \'267180\', 1, \'Analysistimesec\', \'1.083460\', 1, \'Analysismemkb\', \'218384.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'1895216\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'184450\', 1, \'Matrixbw\', \'8.696290\', 1, \'Matrixnnz\', \'1604031\', 1, \'Rootdim\', \'731\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'137604996907663360.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.00246876, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 8'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 4, 0, 5, 0, 189440, 'I(1, 2, \'Tetrahedra\', 171653, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 2, 0, 2, 0, 514060, 'I(2, 2, \'Tetrahedra\', 171653, false, 1, \'Disk\', \'69 KB\')', true, true)
				ProfileItem('Matrix Assembly', 2, 0, 4, 0, 627132, 'I(3, 2, \'Tetrahedra\', 171653, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 4, 0, 18, 0, 2071460, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 200632, false, 3, \'Matrix bandwidth\', 8.69339, \'%5.1f\', 1, \'Disk\', \'785 KB\')', true, true)
				ProfileItem('Field Recovery', 3, 0, 5, 0, 2071460, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.21 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134396, 'I(1, 0, \'Adaptive Pass 8\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427236')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.151805\', 1, \'Fbscputimesec\', \'0.455414\', 1, \'Fbsmemorytotalkb\', \'1481560.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'3.505030\', 1, \'Factorizationmentotalkb\', \'1360370.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'19991\', 1, \'Factornnz\', \'61021644\', 1, \'Factorestflops\', \'126880850640\', 1, \'Fbsestflops\', \'238921275\', 1, \'Rootfactestflops\', \'164973054\', 1, \'Rootfbsestflops\', \'312840\', 1, \'Analysistimesec\', \'1.136560\', 1, \'Analysismemkb\', \'241756.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2071460\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'200632\', 1, \'Matrixbw\', \'8.695950\', 1, \'Matrixnnz\', \'1744685\', 1, \'Rootdim\', \'791\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'135234003161579520.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.00199419, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 9'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 5, 0, 6, 0, 199784, 'I(1, 2, \'Tetrahedra\', 184914, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 2, 0, 2, 0, 542168, 'I(2, 2, \'Tetrahedra\', 184914, false, 1, \'Disk\', \'72.3 KB\')', true, true)
				ProfileItem('Matrix Assembly', 2, 0, 4, 0, 664320, 'I(3, 2, \'Tetrahedra\', 184914, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 5, 0, 20, 0, 2300544, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 216124, false, 3, \'Matrix bandwidth\', 8.69406, \'%5.1f\', 1, \'Disk\', \'846 KB\')', true, true)
				ProfileItem('Field Recovery', 1, 0, 5, 0, 2300544, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.37 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134400, 'I(1, 0, \'Adaptive Pass 9\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427259')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.158640\', 1, \'Fbscputimesec\', \'0.475921\', 1, \'Fbsmemorytotalkb\', \'1676990.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'4.038570\', 1, \'Factorizationmentotalkb\', \'1546220.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'21485\', 1, \'Factornnz\', \'68798095\', 1, \'Factorestflops\', \'151039374955\', 1, \'Fbsestflops\', \'270902487\', 1, \'Rootfactestflops\', \'161247614\', 1, \'Rootfbsestflops\', \'308112\', 1, \'Analysistimesec\', \'1.218390\', 1, \'Analysismemkb\', \'241032.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2300544\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'216124\', 1, \'Matrixbw\', \'8.696510\', 1, \'Matrixnnz\', \'1879524\', 1, \'Rootdim\', \'785\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'131490002860244992.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.000597035, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 10'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 10, 0, 10, 0, 284616, 'I(1, 2, \'Tetrahedra\', 240389, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 3, 0, 3, 0, 664136, 'I(2, 2, \'Tetrahedra\', 240389, false, 1, \'Disk\', \'92.9 KB\')', true, true)
				ProfileItem('Matrix Assembly', 3, 0, 6, 0, 819072, 'I(3, 2, \'Tetrahedra\', 240389, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'300 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 9, 0, 33, 0, 3027532, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 280972, false, 3, \'Matrix bandwidth\', 8.69482, \'%5.1f\', 1, \'Disk\', \'1.07 MB\')', true, true)
				ProfileItem('Field Recovery', 2, 0, 6, 0, 3027532, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'9.71 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134400, 'I(1, 0, \'Adaptive Pass 10\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427290')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.321584\', 1, \'Fbscputimesec\', \'0.964752\', 1, \'Fbsmemorytotalkb\', \'2264890.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'7.107630\', 1, \'Factorizationmentotalkb\', \'2335650.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'27971\', 1, \'Factornnz\', \'104522438\', 1, \'Factorestflops\', \'290017446033\', 1, \'Fbsestflops\', \'439176742\', 1, \'Rootfactestflops\', \'337351830\', 1, \'Rootfbsestflops\', \'504008\', 1, \'Analysistimesec\', \'1.731940\', 1, \'Analysismemkb\', \'274848.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'3027532\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'280972\', 1, \'Matrixbw\', \'8.696930\', 1, \'Matrixnnz\', \'2443594\', 1, \'Rootdim\', \'1004\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'124799998591238144.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.00103148, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 11'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 14, 0, 14, 0, 356412, 'I(1, 2, \'Tetrahedra\', 312514, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 4, 0, 4, 0, 819604, 'I(2, 2, \'Tetrahedra\', 312514, false, 1, \'Disk\', \'118 KB\')', true, true)
				ProfileItem('Matrix Assembly', 3, 0, 7, 0, 1018604, 'I(3, 2, \'Tetrahedra\', 312514, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'300 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 14, 0, 54, 0, 4106160, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 365248, false, 3, \'Matrix bandwidth\', 8.69609, \'%5.1f\', 1, \'Disk\', \'1.39 MB\')', true, true)
				ProfileItem('Field Recovery', 3, 0, 8, 0, 4106160, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'12.7 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134400, 'I(1, 0, \'Adaptive Pass 11\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427334')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.465711\', 1, \'Fbscputimesec\', \'1.397130\', 1, \'Fbsmemorytotalkb\', \'3161910.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'11.918800\', 1, \'Factorizationmentotalkb\', \'3477170.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'36404\', 1, \'Factornnz\', \'155491187\', 1, \'Factorestflops\', \'543374055364\', 1, \'Fbsestflops\', \'679205089\', 1, \'Rootfactestflops\', \'528416917\', 1, \'Rootfbsestflops\', \'679778\', 1, \'Analysistimesec\', \'2.315160\', 1, \'Analysismemkb\', \'387176.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'4106160\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'365248\', 1, \'Matrixbw\', \'8.697880\', 1, \'Matrixnnz\', \'3176885\', 1, \'Rootdim\', \'1166\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'124142001011556352.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.000821608, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 12'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 17, 0, 18, 0, 452756, 'I(1, 2, \'Tetrahedra\', 406270, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 5, 0, 5, 0, 1022392, 'I(2, 2, \'Tetrahedra\', 406270, false, 1, \'Disk\', \'155 KB\')', true, true)
				ProfileItem('Matrix Assembly', 4, 0, 10, 0, 1279936, 'I(3, 2, \'Tetrahedra\', 406270, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'375 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 24, 0, 89, 0, 5664068, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 474849, false, 3, \'Matrix bandwidth\', 8.69632, \'%5.1f\', 1, \'Disk\', \'1.81 MB\')', true, true)
				ProfileItem('Field Recovery', 4, 0, 10, 0, 5664068, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'16.5 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134408, 'I(1, 0, \'Adaptive Pass 12\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427395')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.555631\', 1, \'Fbscputimesec\', \'1.666890\', 1, \'Fbsmemorytotalkb\', \'4480060.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'20.130300\', 1, \'Factorizationmentotalkb\', \'5071040.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'47217\', 1, \'Factornnz\', \'231734989\', 1, \'Factorestflops\', \'968731551465\', 1, \'Fbsestflops\', \'1024511136\', 1, \'Rootfactestflops\', \'727278029\', 1, \'Rootfbsestflops\', \'841104\', 1, \'Analysistimesec\', \'3.245120\', 1, \'Analysismemkb\', \'476016.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'5664068\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'474849\', 1, \'Matrixbw\', \'8.697860\', 1, \'Matrixnnz\', \'4130172\', 1, \'Rootdim\', \'1297\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'134038000798531584.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.000706881, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 13'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 22, 0, 23, 0, 556244, 'I(1, 2, \'Tetrahedra\', 528156, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 7, 0, 7, 0, 1288136, 'I(2, 2, \'Tetrahedra\', 528156, false, 1, \'Disk\', \'206 KB\')', true, true)
				ProfileItem('Matrix Assembly', 6, 0, 12, 0, 1619588, 'I(3, 2, \'Tetrahedra\', 528156, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'1.1 KB\')', true, true)
				ProfileItem('Matrix Solve', 37, 0, 141, 0, 7936840, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 617378, false, 3, \'Matrix bandwidth\', 8.69555, \'%5.1f\', 1, \'Disk\', \'2.36 MB\')', true, true)
				ProfileItem('Field Recovery', 5, 0, 13, 0, 7936840, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'21.6 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134416, 'I(1, 0, \'Adaptive Pass 13\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427479')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.694626\', 1, \'Fbscputimesec\', \'2.083880\', 1, \'Fbsmemorytotalkb\', \'6447350.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'32.698100\', 1, \'Factorizationmentotalkb\', \'7369620.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'61468\', 1, \'Factornnz\', \'337125902\', 1, \'Factorestflops\', \'1692222819766\', 1, \'Fbsestflops\', \'1617879971\', 1, \'Rootfactestflops\', \'1156798537\', 1, \'Rootfbsestflops\', \'1146098\', 1, \'Analysistimesec\', \'4.279340\', 1, \'Analysismemkb\', \'524900.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'7936840\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'617378\', 1, \'Matrixbw\', \'8.696990\', 1, \'Matrixnnz\', \'5369328\', 1, \'Rootdim\', \'1514\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'123597004021432320.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.000256771, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 14'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 21, 0, 22, 0, 594524, 'I(1, 2, \'Tetrahedra\', 625488, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 7, 0, 7, 0, 1505748, 'I(2, 2, \'Tetrahedra\', 625488, false, 1, \'Disk\', \'240 KB\')', true, true)
				ProfileItem('Matrix Assembly', 7, 0, 14, 0, 1893544, 'I(3, 2, \'Tetrahedra\', 625488, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'300 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 52, 0, 196, 0, 9695976, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 731333, false, 3, \'Matrix bandwidth\', 8.69397, \'%5.1f\', 1, \'Disk\', \'2.79 MB\')', true, true)
				ProfileItem('Field Recovery', 6, 0, 14, 0, 9695976, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'20.7 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134420, 'I(1, 0, \'Adaptive Pass 14\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427581')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'0.889177\', 1, \'Fbscputimesec\', \'2.667530\', 1, \'Fbsmemorytotalkb\', \'7951350.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'46.140900\', 1, \'Factorizationmentotalkb\', \'9383550.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'72652\', 1, \'Factornnz\', \'427624220\', 1, \'Factorestflops\', \'2372540267496\', 1, \'Fbsestflops\', \'2029613564\', 1, \'Rootfactestflops\', \'1367898886\', 1, \'Rootfbsestflops\', \'1281600\', 1, \'Analysistimesec\', \'5.280430\', 1, \'Analysismemkb\', \'646008.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'9695976\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'731333\', 1, \'Matrixbw\', \'8.695320\', 1, \'Matrixnnz\', \'6359171\', 1, \'Rootdim\', \'1601\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'129446002154274816.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.000167076, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 15'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 21, 0, 22, 0, 626868, 'I(1, 2, \'Tetrahedra\', 702127, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 9, 0, 9, 0, 1661576, 'I(2, 2, \'Tetrahedra\', 702127, false, 1, \'Disk\', \'273 KB\')', true, true)
				ProfileItem('Matrix Assembly', 8, 0, 16, 0, 2100776, 'I(3, 2, \'Tetrahedra\', 702127, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'75 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 64, 0, 243, 0, 11414516, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 821070, false, 3, \'Matrix bandwidth\', 8.69308, \'%5.1f\', 1, \'Disk\', \'3.13 MB\')', true, true)
				ProfileItem('Field Recovery', 7, 0, 16, 0, 11414516, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'19.8 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134464, 'I(1, 0, \'Adaptive Pass 15\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427698')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'1.416620\', 1, \'Fbscputimesec\', \'4.249870\', 1, \'Fbsmemorytotalkb\', \'9483530.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'57.388000\', 1, \'Factorizationmentotalkb\', \'11314300.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'81499\', 1, \'Factornnz\', \'509928406\', 1, \'Factorestflops\', \'3150150319426\', 1, \'Fbsestflops\', \'2559006550\', 1, \'Rootfactestflops\', \'2193756910\', 1, \'Rootfbsestflops\', \'1755938\', 1, \'Analysistimesec\', \'5.802640\', 1, \'Analysismemkb\', \'756924.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'11414516\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'821070\', 1, \'Matrixbw\', \'8.694330\', 1, \'Matrixnnz\', \'7138651\', 1, \'Rootdim\', \'1874\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'137004002133934080.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.000282762, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 16'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 33, 0, 35, 0, 844192, 'I(1, 2, \'Tetrahedra\', 865905, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 11, 0, 11, 0, 2022116, 'I(2, 2, \'Tetrahedra\', 865905, false, 1, \'Disk\', \'343 KB\')', true, true)
				ProfileItem('Matrix Assembly', 10, 0, 19, 0, 2562448, 'I(3, 2, \'Tetrahedra\', 865905, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'675 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 94, 0, 359, 0, 14843852, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 1012803, false, 3, \'Matrix bandwidth\', 8.69169, \'%5.1f\', 1, \'Disk\', \'3.87 MB\')', true, true)
				ProfileItem('Field Recovery', 9, 0, 19, 0, 14843852, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'31.7 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134476, 'I(1, 0, \'Adaptive Pass 16\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781427863')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'1.397030\', 1, \'Fbscputimesec\', \'4.191100\', 1, \'Fbsmemorytotalkb\', \'12497900.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'85.825500\', 1, \'Factorizationmentotalkb\', \'14570800.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'100608\', 1, \'Factornnz\', \'678889758\', 1, \'Factorestflops\', \'4818349386632\', 1, \'Fbsestflops\', \'3408842763\', 1, \'Rootfactestflops\', \'2913943924\', 1, \'Rootfbsestflops\', \'2121800\', 1, \'Analysistimesec\', \'7.223170\', 1, \'Analysismemkb\', \'857700.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'14843852\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1012803\', 1, \'Matrixbw\', \'8.692870\', 1, \'Matrixnnz\', \'8804163\', 1, \'Rootdim\', \'2060\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'123434001422614528.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.000511205, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Adaptive Pass 17'
				$begin 'StartInfo'
					I(1, 'Frequency', '6.78MHz')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(0, ' ')
				$end 'TotalInfo'
				GroupOptions=0
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('Adaptive Refine', 27, 0, 29, 0, 817388, 'I(1, 2, \'Tetrahedra\', 953673, false)', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('Simulation Setup ', 12, 0, 12, 0, 2237396, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'338 KB\')', true, true)
				ProfileItem('Matrix Assembly', 11, 0, 21, 0, 2824008, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'675 Bytes\')', true, true)
				ProfileItem('Matrix Solve', 114, 0, 433, 0, 16625224, 'I(5, 1, \'Type\', \'DCS\', 2, \'Cores\', 4, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 1, \'Disk\', \'4.26 MB\')', true, true)
				ProfileItem('Field Recovery', 10, 0, 22, 0, 16625224, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'25.3 MB\')', true, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 134488, 'I(1, 0, \'Adaptive Pass 17\')', true, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='APIPms'
					$begin 'StartInfo'
						I(1, 'Timesinceepock', '1781428047')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, ' ')
					$end 'TotalInfo'
					GroupOptions=16
					TaskDataOptions(Memory=8)
					ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'fullsolve\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'false\', 1, \'Fbsnumcores\', \'4\', 1, \'Fbsnumsolvestotal\', \'4\', 1, \'Fbsnumsolves\', \'3\', 1, \'Fbsavgsolvetime1solvesec\', \'2.044940\', 1, \'Fbscputimesec\', \'6.134810\', 1, \'Fbsmemorytotalkb\', \'14033700.000000\')', false, true)
					ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'4\', 1, \'Factorizationtimesec\', \'103.643000\', 1, \'Factorizationmentotalkb\', \'16657300.000000\')', false, true)
					ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110682\', 1, \'Factornnz\', \'774507826\', 1, \'Factorestflops\', \'5822896141383\', 1, \'Fbsestflops\', \'4053167436\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'8.224480\', 1, \'Analysismemkb\', \'893612.000000\')', false, true)
					ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'16657257\', 1, \'Maxdiskkb\', \'0\')', false, true)
					ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
					ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'132020001824571392.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
				$end 'ProfileGroup'
				ProfileFootnote('I(1, 3, \'Max Mag. Delta S\', 0.000259141, \'%.5f\')', 0)
			$end 'ProfileGroup'
			ProfileFootnote('I(1, 0, \'Adaptive Passes converged\')', 0)
		$end 'ProfileGroup'
		$begin 'ProfileGroup'
			MajorVer=2025
			MinorVer=2
			Name='Frequency Sweep'
			$begin 'StartInfo'
				I(1, 'Time', '06/14/2026 09:07:49')
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(1, 'Elapsed Time', '00:30:39')
			$end 'TotalInfo'
			GroupOptions=4
			TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
			ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 1, \'HPC\', \'Enabled\')', false, true)
			$begin 'ProfileGroup'
				MajorVer=2025
				MinorVer=2
				Name='Solution - Sweep'
				$begin 'StartInfo'
					I(0, 'Interpolating HFSS Frequency Sweep, Solving Distributed - up to 4 frequencies in parallel')
					I(1, 'Time', '06/14/2026 09:07:49')
				$end 'StartInfo'
				$begin 'TotalInfo'
					I(1, 'Elapsed Time', '00:30:39')
				$end 'TotalInfo'
				GroupOptions=4
				TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'From 100kHz to 100MHz, 81 Frequencies\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Using automatic algorithm to locate minimum frequency for the sweep.\')', false, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 10MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:50')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #1; Automatic determination of minimum frequency\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2119312, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 16, 0, 16, 0, 2381980, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 380, 0, 379, 0, 5282472, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'4.26 MB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5282472, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781428484')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.008532\', 1, \'Fbscputimesec\', \'0.008532\', 1, \'Fbsmemorytotalkb\', \'2682220.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'363.093000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'16.710400\', 1, \'Analysismemkb\', \'721744.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2682220\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'124537996996247552.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 5.5MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:53')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #1; Automatic determination of minimum frequency\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2119608, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 16, 0, 15, 0, 2382716, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 383, 0, 382, 0, 5291000, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'4.26 MB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5291000, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781428488')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.005708\', 1, \'Fbscputimesec\', \'0.005708\', 1, \'Fbsmemorytotalkb\', \'2690230.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'366.329000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'16.775500\', 1, \'Analysismemkb\', \'721904.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2690228\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'138802004293058560.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 1MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:52')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #1; Automatic determination of minimum frequency\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2118220, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2381084, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 381, 0, 381, 0, 5287832, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'4.26 MB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5287832, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781428487')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.009799\', 1, \'Fbscputimesec\', \'0.009799\', 1, \'Fbsmemorytotalkb\', \'2688980.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'364.891000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'16.699500\', 1, \'Analysismemkb\', \'721920.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2688980\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'133970002876301312.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 550kHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:08:41')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #1; Automatic determination of minimum frequency\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2117104, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Port 1 supports an additional propagating and/or slowly decaying mode whose attenuation is   2.487e-08 and propagation constant is  -1.171e+02\')', false, true)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Port 1 supports an additional propagating and/or slowly decaying mode whose attenuation is   4.385e-06 and propagation constant is  -7.068e+02\')', false, true)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Port 2 supports an additional propagating and/or slowly decaying mode whose attenuation is   2.242e-08 and propagation constant is  -1.200e+02\')', false, true)
					ProfileItem('Matrix Assembly', 28, 0, 28, 0, 2482508, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 478, 0, 478, 0, 5955156, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 13.5906, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'4.26 MB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5955156, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781428597')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.008597\', 1, \'Fbscputimesec\', \'0.008597\', 1, \'Fbsmemorytotalkb\', \'3142800.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'451.252000\', 1, \'Factorizationmentotalkb\', \'3007800.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'112793\', 1, \'Factornnz\', \'950164618\', 1, \'Factorestflops\', \'8154098031218\', 1, \'Fbsestflops\', \'5149877709\', 1, \'Rootfactestflops\', \'5417324638\', 1, \'Rootfbsestflops\', \'3208044\', 1, \'Analysistimesec\', \'26.993700\', 1, \'Analysismemkb\', \'1061030.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'3142800\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'13.591800\', 1, \'Matrixnnz\', \'15162872\', 1, \'Rootdim\', \'2533\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'139506997404893184.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 100kHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:08:10')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #2; Automatic determination of minimum frequency\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2119836, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Port 1 supports an additional propagating and/or slowly decaying mode whose attenuation is   1.780e-07 and propagation constant is  -7.068e+02\')', false, true)
					ProfileItem('Matrix Assembly', 28, 0, 28, 0, 2484768, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 447, 0, 446, 0, 5919364, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 13.5906, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5919364, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781429103')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.008538\', 1, \'Fbscputimesec\', \'0.008538\', 1, \'Fbsmemorytotalkb\', \'3105580.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'442.329000\', 1, \'Factorizationmentotalkb\', \'3007800.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'112793\', 1, \'Factornnz\', \'950164618\', 1, \'Factorestflops\', \'8154098031218\', 1, \'Fbsestflops\', \'5149877709\', 1, \'Rootfactestflops\', \'5417324638\', 1, \'Rootfbsestflops\', \'3208044\', 1, \'Analysistimesec\', \'4.100940\', 1, \'Analysismemkb\', \'412908.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'3105584\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'13.591800\', 1, \'Matrixnnz\', \'15162872\', 1, \'Rootdim\', \'2533\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'135625996236750848.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 50.5MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:19')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #2; Automatic determination of minimum frequency\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2120308, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2384456, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 348, 0, 348, 0, 5272720, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5272720, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781428992')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.009349\', 1, \'Fbscputimesec\', \'0.009349\', 1, \'Fbsmemorytotalkb\', \'2670820.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'346.023000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.569770\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2670816\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'139696001735720960.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 100MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:18')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #2; Automatic determination of minimum frequency\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2118828, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2381224, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 348, 0, 348, 0, 5269860, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5269860, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781428992')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.012065\', 1, \'Fbscputimesec\', \'0.012065\', 1, \'Fbsmemorytotalkb\', \'2670960.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'345.439000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.624250\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2670960\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'127696000549650432.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 25.75MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:18')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #2; Automatic determination of minimum frequency\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2118588, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2381292, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 348, 0, 347, 0, 5269492, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5269492, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.65 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781428992')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.007131\', 1, \'Fbscputimesec\', \'0.007131\', 1, \'Fbsmemorytotalkb\', \'2670160.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'345.371000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.615610\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2670160\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'123547002012172288.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 1, Frequency: 100MHz; Additional basis points are needed before the interpolation error can be computed.\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 2, Frequency: 100kHz; Additional basis points are needed before the interpolation error can be computed.\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 3, Frequency: 50.5MHz; S Matrix Error = 236.836%\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 4, Frequency: 25.75MHz; S Matrix Error = 205.479%\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 5, Frequency: 10MHz; New subrange(s) added; Additional basis points are needed before the interpolation error can be computed.\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 6, Frequency: 5.5MHz; S Matrix Error = 131.089%\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 7, Frequency: 1MHz; New subrange(s) added; Additional basis points are needed before the interpolation error can be computed.\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 8, Frequency: 550kHz; S Matrix Error = 132.317%\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Frequency: 6.78MHz has already been solved\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 9, Frequency: 6.78MHz; S Matrix Error = 145.451%\')', false, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 75.25MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:17')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #3\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2118028, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2381180, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 348, 0, 348, 0, 5270228, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5270228, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781429497')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.008665\', 1, \'Fbscputimesec\', \'0.008665\', 1, \'Fbsmemorytotalkb\', \'2671480.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'345.679000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.680520\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2671476\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'136007002785579008.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 38.125MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:20')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #3\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2121744, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2385220, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 350, 0, 349, 0, 5272812, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5272812, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781429499')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.006382\', 1, \'Fbscputimesec\', \'0.006382\', 1, \'Fbsmemorytotalkb\', \'2671000.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'347.346000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.714910\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2671000\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'124679997204987904.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 17.875MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:19')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #3\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2117024, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2380116, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 349, 0, 348, 0, 5269032, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5269032, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781429499')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.007631\', 1, \'Fbscputimesec\', \'0.007631\', 1, \'Fbsmemorytotalkb\', \'2670510.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'346.440000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.663590\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2670512\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'124176996405084160.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 62.875MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:19')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #3\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2117696, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2380716, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 349, 0, 349, 0, 5269588, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5269588, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781429500')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.006322\', 1, \'Fbscputimesec\', \'0.006322\', 1, \'Fbsmemorytotalkb\', \'2671440.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'346.733000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.814250\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2671444\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'125928003032055808.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 10, Frequency: 75.25MHz; S Matrix Error =  13.522%\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 11, Frequency: 38.125MHz; S Matrix Error =   2.611%\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 12, Frequency: 17.875MHz; S Matrix Error =   1.764%\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 13, Frequency: 62.875MHz; S Matrix Error =   0.847%\')', false, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 136148, 'I(1, 0, \'Frequency Group #3; Interpolating frequency sweep\')', true, true)
				ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 87.625MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:20')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #4\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2120256, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 16, 0, 16, 0, 2383116, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 350, 0, 349, 0, 5263600, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5263600, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781429896')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.007727\', 1, \'Fbscputimesec\', \'0.007727\', 1, \'Fbsmemorytotalkb\', \'2663090.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'347.139000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.706630\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2663092\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'132911001380061184.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 69.0625MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:22')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #4\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2121216, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2384368, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 352, 0, 351, 0, 5272800, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5272800, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781429898')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.008134\', 1, \'Fbscputimesec\', \'0.008134\', 1, \'Fbsmemorytotalkb\', \'2671760.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'349.040000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.665610\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2671760\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'140218003470942208.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 56.6875MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:21')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #4\')', false, true)
					ProfileItem(' ', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2118628, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2381984, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 351, 0, 350, 0, 5280804, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5280804, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781429898')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.014239\', 1, \'Fbscputimesec\', \'0.014239\', 1, \'Fbsmemorytotalkb\', \'2682070.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'348.433000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.662430\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2682072\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'126321997561987072.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				$begin 'ProfileGroup'
					MajorVer=2025
					MinorVer=2
					Name='Frequency - 13.9375MHz'
					$begin 'StartInfo'
						I(0, 'harrypc')
					$end 'StartInfo'
					$begin 'TotalInfo'
						I(0, 'Elapsed time : 00:06:21')
					$end 'TotalInfo'
					GroupOptions=0
					TaskDataOptions('CPU Time'=8, 'Real Time'=8)
					ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Distributed Solve Group #4\')', false, true)
					ProfileItem('Simulation Setup ', 13, 0, 13, 0, 2118136, 'I(2, 2, \'Tetrahedra\', 953673, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Assembly', 15, 0, 15, 0, 2380824, 'I(3, 2, \'Tetrahedra\', 953673, false, 2, \'Lumped ports\', 2, false, 1, \'Disk\', \'0 Bytes\')', true, false)
					ProfileItem('Matrix Solve', 351, 0, 350, 0, 5270344, 'I(6, 1, \'Type\', \'DCS\', 2, \'Cores\', 1, false, 2, \'Matrix size\', 1115588, false, 3, \'Matrix bandwidth\', 8.69078, \'%5.1f\', 2, \'S-matrix only solve\', 2, false, 1, \'Disk\', \'1.63 KB\')', true, false)
					ProfileItem('Field Recovery', 0, 0, 0, 0, 5270344, 'I(2, 2, \'Excitations\', 2, false, 1, \'Disk\', \'4.64 KB\')', true, false)
					$begin 'ProfileGroup'
						MajorVer=2025
						MinorVer=2
						Name='APIPms1'
						$begin 'StartInfo'
							I(1, 'Timesinceepock', '1781429898')
						$end 'StartInfo'
						$begin 'TotalInfo'
							I(0, ' ')
						$end 'TotalInfo'
						GroupOptions=16
						TaskDataOptions('CPU Time'=8, 'Real Time'=8)
						ProfileItem('fbsinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Fbstatus\', \'valid\', 1, \'Fbstype\', \'partial_dense\', 1, \'Fbsmt\', \'false\', 1, \'Fbsmrhs\', \'true\', 1, \'Fbsnumcores\', \'1\', 1, \'Fbsnumsolvestotal\', \'2\', 1, \'Fbsnumsolves\', \'1\', 1, \'Fbsavgsolvetime1solvesec\', \'0.007575\', 1, \'Fbscputimesec\', \'0.007575\', 1, \'Fbsmemorytotalkb\', \'2671580.000000\')', false, true)
						ProfileItem('factorinfo', 0, 0, 0, 0, 0, 'I(4, 1, \'Fatorizationstatus\', \'valid\', 1, \'Factorizationnumcores\', \'1\', 1, \'Factorizationtimesec\', \'348.075000\', 1, \'Factorizationmentotalkb\', \'2639640.000000\')', false, true)
						ProfileItem('analysisinfo', 0, 0, 0, 0, 0, 'I(9, 1, \'Analysisstatus\', \'valid\', 1, \'Numsupernodes\', \'110886\', 1, \'Factornnz\', \'784365975\', 1, \'Factorestflops\', \'5966825659925\', 1, \'Fbsestflops\', \'4056785460\', 1, \'Rootfactestflops\', \'3593077898\', 1, \'Rootfbsestflops\', \'2439840\', 1, \'Analysistimesec\', \'2.624940\', 1, \'Analysismemkb\', \'284779.000000\')', false, true)
						ProfileItem('solverprofile', 0, 0, 0, 0, 0, 'I(2, 1, \'Maxmemkb\', \'2671576\', 1, \'Maxdiskkb\', \'0\')', false, true)
						ProfileItem('solverinfo', 0, 0, 0, 0, 0, 'I(10, 1, \'Solvertype\', \'shared_memory\', 1, \'Precision\', \'double\', 1, \'Solversymmetry\', \'complex_sym\', 1, \'Matrixdim\', \'1115588\', 1, \'Matrixbw\', \'8.691960\', 1, \'Matrixnnz\', \'9696641\', 1, \'Rootdim\', \'2209\', 1, \'Mathtype\', \'amd\', 1, \'Mpitasks\', \'1\', 1, \'Threadspertasks\', \'0\')', false, true)
						ProfileItem('sysinfo', 0, 0, 0, 0, 0, 'I(12, 1, \'Os\', \'lin\', 1, \'Cpuid\', \'AMD Ryzen 9 5950X 16-Core Processor            \', 1, \'CpuPhysicCores\', \'16\', 1, \'CpuLogicCores\', \'32\', 1, \'Cpufreqkhz\', \'133197999684714496.000000\', 1, \'Cpucachelinesizebytes\', \'64\', 1, \'Cpuestlastlevelcachesizemb\', \'64.000000\', 1, \'Cpuestgflops\', \'408.000000\', 1, \'Memorybwestkbps\', \'51.200001\', 1, \'Numanodes\', \'1\', 1, \'Virtualmemkb\', \'-1.000000\', 1, \'Pagesizekb\', \'4096\')', false, true)
					$end 'ProfileGroup'
				$end 'ProfileGroup'
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 14, Frequency: 87.625MHz; S Matrix Error =   8.937%\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 15, Frequency: 69.0625MHz; S Matrix Error =   8.445%\')', false, true)
				ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'Basis Element # 16, Frequency: 56.6875MHz; Scattering matrix quantities converged; Passive within tolerance\')', false, true)
				ProfileItem('Data Transfer', 0, 0, 0, 0, 136168, 'I(1, 0, \'Frequency Group #4; Interpolating frequency sweep\')', true, true)
				ProfileFootnote('I(1, 0, \'Interpolating sweep converged and is passive\')', 0)
				ProfileFootnote('I(1, 0, \'HFSS: Distributed Interpolating sweep\')', 0)
			$end 'ProfileGroup'
		$end 'ProfileGroup'
		ProfileItem('', 0, 0, 0, 0, 0, 'I(1, 0, \'\')', false, true)
		$begin 'ProfileGroup'
			MajorVer=2025
			MinorVer=2
			Name='Simulation Summary'
			$begin 'StartInfo'
			$end 'StartInfo'
			$begin 'TotalInfo'
				I(0, ' ')
			$end 'TotalInfo'
			GroupOptions=0
			TaskDataOptions('CPU Time'=8, Memory=8, 'Real Time'=8)
			ProfileItem('Design Validation', 0, 0, 0, 0, 0, 'I(2, 1, \'Elapsed Time\', \'00:00:00\', 1, \'Total Memory\', \'121 MB\')', false, true)
			ProfileItem('Initial Meshing', 0, 0, 0, 0, 0, 'I(2, 1, \'Elapsed Time\', \'00:00:16\', 1, \'Total Memory\', \'389 MB\')', false, true)
			ProfileItem('Adaptive Meshing', 0, 0, 0, 0, 0, 'I(5, 1, \'Elapsed Time\', \'00:15:35\', 1, \'Average memory/process\', \'15.9 GB\', 1, \'Max memory/process\', \'15.9 GB\', 2, \'Max number of processes/frequency\', 1, false, 2, \'Total number of cores\', 4, false)', false, true)
			ProfileItem('Frequency Sweep', 0, 0, 0, 0, 0, 'I(5, 1, \'Elapsed Time\', \'00:30:39\', 1, \'Average memory/process\', \'5.11 GB\', 1, \'Max memory/process\', \'5.68 GB\', 2, \'Max number of processes/frequency\', 1, false, 2, \'Total number of cores\', 4, false)', false, true)
			ProfileFootnote('I(3, 2, \'Max solved tets\', 953673, false, 2, \'Max matrix size\', 1115588, false, 1, \'Matrix bandwidth\', \'8.7\')', 0)
		$end 'ProfileGroup'
		ProfileFootnote('I(2, 1, \'Stop Time\', \'06/14/2026 09:38:29\', 1, \'Status\', \'Normal Completion\')', 0)
	$end 'ProfileGroup'
$end 'Profile'
