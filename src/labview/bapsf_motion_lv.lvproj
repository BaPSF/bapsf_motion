<?xml version='1.0' encoding='UTF-8'?>
<Project Type="Project" LVVersion="22308000">
	<Property Name="SMProvider.SMVersion" Type="Int">201310</Property>
	<Item Name="My Computer" Type="My Computer">
		<Property Name="IOScan.Faults" Type="Str"></Property>
		<Property Name="IOScan.NetVarPeriod" Type="UInt">100</Property>
		<Property Name="IOScan.NetWatchdogEnabled" Type="Bool">false</Property>
		<Property Name="IOScan.Period" Type="UInt">10000</Property>
		<Property Name="IOScan.PowerupMode" Type="UInt">0</Property>
		<Property Name="IOScan.Priority" Type="UInt">9</Property>
		<Property Name="IOScan.ReportModeConflict" Type="Bool">true</Property>
		<Property Name="IOScan.StartEngineOnDeploy" Type="Bool">false</Property>
		<Property Name="server.app.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="server.control.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="server.tcp.enabled" Type="Bool">false</Property>
		<Property Name="server.tcp.port" Type="Int">0</Property>
		<Property Name="server.tcp.serviceName" Type="Str">My Computer/VI Server</Property>
		<Property Name="server.tcp.serviceName.default" Type="Str">My Computer/VI Server</Property>
		<Property Name="server.vi.callsEnabled" Type="Bool">true</Property>
		<Property Name="server.vi.propertiesEnabled" Type="Bool">true</Property>
		<Property Name="specify.custom.address" Type="Bool">false</Property>
		<Item Name="__pycache__" Type="Folder"/>
		<Item Name="labview" Type="Folder">
			<Item Name="helpers" Type="Folder" URL="../helpers">
				<Property Name="NI.DISK" Type="Bool">true</Property>
			</Item>
			<Item Name="requests" Type="Folder" URL="../requests">
				<Property Name="NI.DISK" Type="Bool">true</Property>
			</Item>
			<Item Name="typedefs" Type="Folder" URL="../typedefs">
				<Property Name="NI.DISK" Type="Bool">true</Property>
			</Item>
			<Item Name="utils" Type="Folder" URL="../utils">
				<Property Name="NI.DISK" Type="Bool">true</Property>
			</Item>
			<Item Name=".DS_Store" Type="Document" URL="../.DS_Store"/>
			<Item Name="_configure.py" Type="Document" URL="../_configure.py"/>
			<Item Name="bapsf_motion.vi" Type="VI" URL="../bapsf_motion.vi"/>
			<Item Name="bapsf_motion_interface.py" Type="Document" URL="../bapsf_motion_interface.py"/>
			<Item Name="bapsf_motion_lv.aliases" Type="Document" URL="../bapsf_motion_lv.aliases"/>
			<Item Name="bapsf_motion_lv.lvlps" Type="Document" URL="../bapsf_motion_lv.lvlps"/>
			<Item Name="configure_dash_.py" Type="Document" URL="../configure_dash_.py"/>
			<Item Name="configure_gui.py" Type="Document" URL="../configure_gui.py"/>
			<Item Name="package-lock.json" Type="Document" URL="../package-lock.json"/>
			<Item Name="README.md" Type="Document" URL="../README.md"/>
			<Item Name="run.log" Type="Document" URL="../run.log"/>
			<Item Name="ShowConsoleForPythonNode.png" Type="Document" URL="../ShowConsoleForPythonNode.png"/>
		</Item>
		<Item Name="Dependencies" Type="Dependencies">
			<Item Name="vi.lib" Type="Folder">
				<Item Name="Clear Errors.vi" Type="VI" URL="/&lt;vilib&gt;/Utility/error.llb/Clear Errors.vi"/>
			</Item>
		</Item>
		<Item Name="Build Specifications" Type="Build"/>
	</Item>
</Project>
