# ----------------------------------------------
# Script Recorded by Ansys Electronics Desktop Version 2025.2.0
# 8:03:25  Jun 17, 2026
# ----------------------------------------------
import ScriptEnv
ScriptEnv.Initialize("Ansoft.ElectronicsDesktop")
oDesktop.RestoreWindow()
oProject = oDesktop.SetActiveProject("0_3_7_p6561d2a5c7808f6e")
oDesign = oProject.SetActiveDesign("Q3D_from_HFSS")
oModule = oDesign.GetModule("ReportSetup")
oModule.CreateReport("Variables Table1", "Matrix", "Data Table", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["Pass"]
	])
oModule.AddTraces("Variables Table1", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["C(rx_ssw_coil_ssw_copper,rx_ssw_coil_ssw_copper)","C(tx_ssw_coil_ssw_copper,rx_ssw_coil_ssw_copper)","C(rx_ssw_coil_ssw_copper,tx_ssw_coil_ssw_copper)","C(tx_ssw_coil_ssw_copper,tx_ssw_coil_ssw_copper)"]
	])
oModule.AddTraces("Variables Table1", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["G(rx_ssw_coil_ssw_copper,rx_ssw_coil_ssw_copper)","G(tx_ssw_coil_ssw_copper,rx_ssw_coil_ssw_copper)","G(rx_ssw_coil_ssw_copper,tx_ssw_coil_ssw_copper)","G(tx_ssw_coil_ssw_copper,tx_ssw_coil_ssw_copper)"]
	])
oModule.AddTraces("Variables Table1", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["DCL(rx_ssw_coil_ssw_copper:rx_src,rx_ssw_coil_ssw_copper:rx_src)","DCL(tx_ssw_coil_ssw_copper:tx_src,rx_ssw_coil_ssw_copper:rx_src)","DCL(rx_ssw_coil_ssw_copper:rx_src,tx_ssw_coil_ssw_copper:tx_src)","DCL(tx_ssw_coil_ssw_copper:tx_src,tx_ssw_coil_ssw_copper:tx_src)"]
	])
oModule.AddTraces("Variables Table1", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["DCR(rx_ssw_coil_ssw_copper:rx_src,rx_ssw_coil_ssw_copper:rx_src)","DCR(tx_ssw_coil_ssw_copper:tx_src,rx_ssw_coil_ssw_copper:rx_src)","DCR(rx_ssw_coil_ssw_copper:rx_src,tx_ssw_coil_ssw_copper:tx_src)","DCR(tx_ssw_coil_ssw_copper:tx_src,tx_ssw_coil_ssw_copper:tx_src)"]
	])
oModule.AddTraces("Variables Table1", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["ACL(rx_ssw_coil_ssw_copper:rx_src,rx_ssw_coil_ssw_copper:rx_src)","ACL(tx_ssw_coil_ssw_copper:tx_src,rx_ssw_coil_ssw_copper:rx_src)","ACL(rx_ssw_coil_ssw_copper:rx_src,tx_ssw_coil_ssw_copper:tx_src)","ACL(tx_ssw_coil_ssw_copper:tx_src,tx_ssw_coil_ssw_copper:tx_src)"]
	])
oModule.AddTraces("Variables Table1", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["ACR(rx_ssw_coil_ssw_copper:rx_src,rx_ssw_coil_ssw_copper:rx_src)","ACR(tx_ssw_coil_ssw_copper:tx_src,rx_ssw_coil_ssw_copper:rx_src)","ACR(rx_ssw_coil_ssw_copper:rx_src,tx_ssw_coil_ssw_copper:tx_src)","ACR(tx_ssw_coil_ssw_copper:tx_src,tx_ssw_coil_ssw_copper:tx_src)"]
	])
oProject.Save()
oDesign.Analyze("Q3DSetup")
oModule = oDesign.GetModule("FieldsReporter")
oModule.CreateFieldPlot(
	[
		"NAME:Mesh1",
		"SolutionName:="	, "Q3DSetup : LastAdaptive",
		"UserSpecifyName:="	, 0,
		"UserSpecifyFolder:="	, 0,
		"QuantityName:="	, "Mesh",
		"PlotFolder:="		, "MeshPlots",
		"FieldType:="		, "CG Fields",
		"StreamlinePlot:="	, False,
		"AdjacentSidePlot:="	, False,
		"FullModelPlot:="	, False,
		"IntrinsicVar:="	, "Freq=\'0.0067799999999999996GHz\' Phase=\'0deg\'",
		"PlotGeomInfo:="	, [1,"Surface","FacesList",200,"659","660","661","662","663","664","665","666","667","668","669","670","671","672","673","674","675","676","677","678","679","680","681","682","683","684","685","686","687","688","689","690","691","692","693","694","695","696","697","698","699","700","701","702","703","704","705","706","707","708","709","710","711","712","713","714","715","716","717","718","719","720","721","722","723","724","725","726","727","728","729","730","731","732","733","734","735","736","737","738","739","740","741","742","743","744","745","746","747","748","749","750","751","752","753","754","755","756","757","758","759","760","7","8","9","10","11","12","13","14","15","16","17","18","19","20","21","22","23","24","25","26","27","28","29","30","31","32","33","34","35","36","37","38","39","40","41","42","43","44","45","46","47","48","49","50","51","52","53","54","55","56","57","58","59","60","61","62","63","64","65","66","67","68","69","70","71","72","73","74","75","76","77","78","79","80","81","82","83","84","85","86","87","88","89","90","91","92","93","94","95","96","97","98","99","100","101","102","103","104"],
		"FilterBoxes:="		, [0],
		"Real time mode:="	, True,
		[
			"NAME:MeshSettings",
			"ShadingType:="		, 0,
			"Scale factor:="	, 100,
			"Transparency:="	, 0,
			"Mesh type:="		, "Shaded",
			"Surface only:="	, True,
			"Add grid:="		, True,
			"Refinement:="		, 0,
			"Use geometry color:="	, True,
			"Mesh line color:="	, [0,0,255],
			"Filled color:="	, [255,255,255]
		],
		"EnableGaussianSmoothing:=", False,
		"SurfaceOnly:="		, False
	], "Field")
oModule = oDesign.GetModule("ReportSetup")
oModule.UpdateReports(["Variables Table1"])
oModule.DeleteReports(["Variables Table1"])
oModule.CreateReport("ACL Matrix Table1", "Matrix", "Data Table", "Q3DSetup : LastAdaptive", 
	[
		"Context:="		, "Original"
	], 
	[
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Freq",
		"Y Component:="		, ["ACL(rx_ssw_coil_ssw_copper:rx_src,rx_ssw_coil_ssw_copper:rx_src)","ACL(tx_ssw_coil_ssw_copper:tx_src,rx_ssw_coil_ssw_copper:rx_src)","ACL(rx_ssw_coil_ssw_copper:rx_src,tx_ssw_coil_ssw_copper:tx_src)","ACL(tx_ssw_coil_ssw_copper:tx_src,tx_ssw_coil_ssw_copper:tx_src)"]
	])
oModule.DeleteReports(["ACL Matrix Table1"])
oModule.CreateReport("ACL Matrix Table1", "Matrix", "Data Table", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["ACL(rx_ssw_coil_ssw_copper:rx_src,rx_ssw_coil_ssw_copper:rx_src)","ACL(tx_ssw_coil_ssw_copper:tx_src,rx_ssw_coil_ssw_copper:rx_src)","ACL(rx_ssw_coil_ssw_copper:rx_src,tx_ssw_coil_ssw_copper:tx_src)","ACL(tx_ssw_coil_ssw_copper:tx_src,tx_ssw_coil_ssw_copper:tx_src)"]
	])
oModule.CreateReport("ACR Matrix Table1", "Matrix", "Data Table", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["ACR(rx_ssw_coil_ssw_copper:rx_src,rx_ssw_coil_ssw_copper:rx_src)","ACR(tx_ssw_coil_ssw_copper:tx_src,rx_ssw_coil_ssw_copper:rx_src)","ACR(rx_ssw_coil_ssw_copper:rx_src,tx_ssw_coil_ssw_copper:tx_src)","ACR(tx_ssw_coil_ssw_copper:tx_src,tx_ssw_coil_ssw_copper:tx_src)"]
	])
oModule.CreateReport("DCL Matrix Table1", "Matrix", "Data Table", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["DCL(rx_ssw_coil_ssw_copper:rx_src,rx_ssw_coil_ssw_copper:rx_src)","DCL(tx_ssw_coil_ssw_copper:tx_src,rx_ssw_coil_ssw_copper:rx_src)","DCL(rx_ssw_coil_ssw_copper:rx_src,tx_ssw_coil_ssw_copper:tx_src)","DCL(tx_ssw_coil_ssw_copper:tx_src,tx_ssw_coil_ssw_copper:tx_src)"]
	])
oModule.CreateReport("DCR Matrix Table1", "Matrix", "Data Table", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["DCR(rx_ssw_coil_ssw_copper:rx_src,rx_ssw_coil_ssw_copper:rx_src)","DCR(tx_ssw_coil_ssw_copper:tx_src,rx_ssw_coil_ssw_copper:rx_src)","DCR(rx_ssw_coil_ssw_copper:rx_src,tx_ssw_coil_ssw_copper:tx_src)","DCR(tx_ssw_coil_ssw_copper:tx_src,tx_ssw_coil_ssw_copper:tx_src)"]
	])
oModule.CreateReport("C Matrix Table1", "Matrix", "Data Table", "Q3DSetup : AdaptivePass", 
	[
		"Context:="		, "Original"
	], 
	[
		"Pass:="		, ["All"],
		"Freq:="		, ["All"]
	], 
	[
		"X Component:="		, "Pass",
		"Y Component:="		, ["C(rx_ssw_coil_ssw_copper,rx_ssw_coil_ssw_copper)","C(tx_ssw_coil_ssw_copper,rx_ssw_coil_ssw_copper)","C(rx_ssw_coil_ssw_copper,tx_ssw_coil_ssw_copper)","C(tx_ssw_coil_ssw_copper,tx_ssw_coil_ssw_copper)"]
	])
oModule.ExportToFile("ACL Matrix Table1", "/home/harry/Downloads/ACL Matrix Table1.csv", False)
oModule.ExportToFile("ACL Matrix Table1", "/home/harry/Downloads/ACL Matrix Table1.csv", False)
oModule.ExportToFile("ACR Matrix Table1", "/home/harry/Downloads/ACR Matrix Table1.csv", False)
oModule.ExportToFile("DCL Matrix Table1", "/home/harry/Downloads/DCL Matrix Table1.csv", False)
oModule.ExportToFile("DCR Matrix Table1", "/home/harry/Downloads/DCR Matrix Table1.csv", False)
oModule.ExportToFile("C Matrix Table1", "/home/harry/Downloads/C Matrix Table1.csv", False)
oProject.Save()
