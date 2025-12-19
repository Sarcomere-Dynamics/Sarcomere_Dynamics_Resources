#include "SDKClient.hpp"
#include "ManusSDKTypes.h"
#include <fstream>
#include <iostream>

#include "ClientPlatformSpecific.hpp"


#include <sstream> // Include this for std::stringstream

#define GO_TO_DISPLAY(p_Key,p_Function) if (GetKeyDown(p_Key)) { ClearConsole();\
		m_CurrentInteraction = std::bind(&SDKClient::p_Function, this); return ClientReturnCode::ClientReturnCode_Success;}

#define GO_TO_MENU_IF_REQUESTED() if (GetKeyDown('Q')) { ClearConsole();\
		m_CurrentInteraction = nullptr; return ClientReturnCode::ClientReturnCode_Success;}


#define TCP_DATA_RATE 50 // Set the data rate for TCP communication (in milliseconds)

//////// TCP Client ////////////////
#pragma comment(lib,"ws2_32.lib") //Winsock Library
TCP_Client::TCP_Client()
{
	sock = INVALID_SOCKET;
	port = 0;
	address = "";
	WSADATA wsa;

	// Initialise winsock
	std::cout << "Initialising Winsock..." << std::endl;
	if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0)
	{
		std::cout << "Failed. Error Code : " << WSAGetLastError() << std::endl;
		exit(EXIT_FAILURE);
	}
	std::cout << "Initialised." << std::endl;
}

/**
	Connect to a host on a certain port number
*/
bool TCP_Client::conn(std::string address, int port)
{
	//create socket if it is not already created
	if (sock == INVALID_SOCKET)
	{
		//Create socket
		sock = socket(AF_INET, SOCK_STREAM, 0);
		if (sock == INVALID_SOCKET)
		{
			std::cout << "Could not create socket : " << WSAGetLastError() << std::endl;
		}

		std::cout << "Socket created\n";
	}
	else {   /* OK , nothing */ }

	//setup address structure
	if (inet_pton(AF_INET, address.c_str(), &server.sin_addr) <= 0)
	{
		std::cout << "Invalid address/ Address not supported" << std::endl;
		return false;
	}

	server.sin_family = AF_INET;
	server.sin_port = htons(port);

	//Connect to remote server
	if (connect(sock, (struct sockaddr*)&server, sizeof(server)) < 0)
	{
		std::cout << "Connect failed. Error: " << WSAGetLastError() << std::endl;
		return false;
	}

	std::cout << "Connected\n";
	return true;
}

/**
	Send data to the connected host
*/
bool TCP_Client::send_data(std::string data)
{
	//Send some data
	if (send(sock, data.c_str(), strlen(data.c_str()), 0) < 0)
	{
		std::cout << "Send failed : " << WSAGetLastError() << std::endl;
		return false;
	}
	std::cout << "Data sent\n";

	return true;
}

/**
	Receive data from the connected host
*/
std::string TCP_Client::receive(int size = 512)
{
	char buffer[512];
	std::string reply;

	//Receive a reply from the server
	if (recv(sock, buffer, size, 0) < 0)
	{
		std::cout << "recv failed: " << WSAGetLastError() << std::endl;
	}

	reply = buffer;
	return reply;
}



//////////////////////////////////////////////////////
SDKClient* SDKClient::s_Instance = nullptr;

SDKClient::SDKClient()
{
	s_Instance = this;

	// using initializers like these ensure that the data is set to its default values.
	ErgonomicsData_Init(&m_LeftGloveErgoData);
	ErgonomicsData_Init(&m_RightGloveErgoData);

	TestTimestamp();
}

SDKClient::~SDKClient()
{
	s_Instance = nullptr;
}

/// @brief Initialize the sample console and the SDK.
/// This function attempts to resize the console window and then proceeds to initialize the SDK's interface.
ClientReturnCode SDKClient::Initialize()
{
	t_tcp_client.conn("127.0.0.1", 65432);
	if (!PlatformSpecificInitialization())
	{
		return ClientReturnCode::ClientReturnCode_FailedPlatformSpecificInitialization;
	}

	// although resizewindow is not technically needed to setup the SDK , it is nice to see what we are doing in this example client.
	// thus we make sure we have a nice console window to use.
	// if this fails, then the window is being resized during startup (due to windows management tools) or by giving it invalid values.
	if (!ResizeWindow(m_ConsoleWidth, m_ConsoleHeight, m_ConsoleScrollback))
	{
		// An error message will be logged in the function, so don't print anything here.
		return ClientReturnCode::ClientReturnCode_FailedToResizeWindow;
	}

	const ClientReturnCode t_IntializeResult = InitializeSDK();

	if (t_IntializeResult != ClientReturnCode::ClientReturnCode_Success)
	{
		spdlog::error("Failed to initialize the Core functionality. The value returned was {}.", t_IntializeResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief The main SDKClient loop.
/// This is a simple state machine which switches between different substates.
ClientReturnCode SDKClient::Run()
{
	ClearConsole();

	ClientReturnCode t_Result{};
	while (!m_RequestedExit)
	{
		if (m_ConsoleClearTickCount >= 100 || m_State != m_PreviousState)
		{
			ClearConsole();

			m_ConsoleClearTickCount = 0;
		}

		UpdateInput();

		// in this example SDK Client we have several phases during our main loop to make sure the SDK is in the right state to work.
		m_PreviousState = m_State;
		switch (m_State)
		{
		case ClientState::ClientState_PickingConnectionType:
		{
			t_Result = PickingConnectionType();
			if (t_Result != ClientReturnCode::ClientReturnCode_Success) { return t_Result; }
		} break;
		case ClientState::ClientState_LookingForHosts:
		{
			t_Result = LookingForHosts();
			if (t_Result != ClientReturnCode::ClientReturnCode_Success &&
				t_Result != ClientReturnCode::ClientReturnCode_FailedToFindHosts) {
				return t_Result;
			}
		} break;
		case ClientState::ClientState_NoHostsFound:
		{
			t_Result = NoHostsFound();
			if (t_Result != ClientReturnCode::ClientReturnCode_Success) { return t_Result; }
		} break;
		case ClientState::ClientState_PickingHost:
		{
			t_Result = PickingHost();
			if (t_Result != ClientReturnCode::ClientReturnCode_Success) { return t_Result; }
		} break;
		case ClientState::ClientState_ConnectingToCore:
		{
			t_Result = ConnectingToCore();
			if (t_Result != ClientReturnCode::ClientReturnCode_Success) { return t_Result; }
		} break;
		case ClientState::ClientState_DisplayingData:
		{
			UpdateBeforeDisplayingData();
			if (m_CurrentInteraction == nullptr)
			{
				t_Result = DisplayingData();
				SendErgonomicsData();
			}
			else
			{
				t_Result = m_CurrentInteraction();
			}
			if (t_Result != ClientReturnCode::ClientReturnCode_Success) { return t_Result; }
		} break;
		case ClientState::ClientState_Disconnected:
		{
			t_Result = DisconnectedFromCore();
			if (t_Result != ClientReturnCode::ClientReturnCode_Success) { return t_Result; }
		}break;
		default:
		{
			spdlog::error("Encountered the unrecognized state {}.", static_cast<int>(m_State));
			return ClientReturnCode::ClientReturnCode_UnrecognizedStateEncountered;
		}
		} // switch(m_State)

		if (GetKeyDown(VK_ESCAPE))
		{
			spdlog::info("Pressed escape, so the client will now close.");

			m_RequestedExit = true;
		}

		m_ConsoleClearTickCount++;
		std::this_thread::sleep_for(std::chrono::milliseconds(10));
	}

	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief When you are done with the SDK, don't forget to nicely shut it down
/// this will close all connections to the host, close any threads and clean up after itself
/// after this is called it is expected to exit the client program. If not it needs to call initialize again.
ClientReturnCode SDKClient::ShutDown()
{
	const SDKReturnCode t_Result = CoreSdk_ShutDown();
	if (t_Result != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to shut down the SDK wrapper. The value returned was {}.", t_Result);
		return ClientReturnCode::ClientReturnCode_FailedToShutDownSDK;
	}

	if (!PlatformSpecificShutdown())
	{
		return ClientReturnCode::ClientReturnCode_FailedPlatformSpecificShutdown;
	}

	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief Gets called when the client is connects to manus core
/// Using this callback is optional.
/// In this sample we use this callback to change the client's state and switch to another screen
void SDKClient::OnConnectedCallback(const ManusHost* const p_Host)
{
	spdlog::info("Connected to manus core.");

	//No need to initialize these as they get filled in the CoreSdk_GetVersionsAndCheckCompatibility
	ManusVersion t_SdkVersion;
	ManusVersion t_CoreVersion;
	bool t_IsCompatible;

	const SDKReturnCode t_Result = CoreSdk_GetVersionsAndCheckCompatibility(&t_SdkVersion, &t_CoreVersion, &t_IsCompatible);

	if (t_Result == SDKReturnCode::SDKReturnCode_Success)
	{
		const std::string t_Versions = "Sdk version : " + std::string(t_SdkVersion.versionInfo) + ", Core version : " + std::string(t_CoreVersion.versionInfo) + ".";

		if (t_IsCompatible)
		{
			spdlog::info("Versions are compatible.{}", t_Versions);
		}
		else
		{
			spdlog::warn("Versions are not compatible with each other.{}", t_Versions);
		}
	}
	else
	{
		spdlog::error("Failed to get the versions from the SDK. The value returned was {}.", t_Result);
	}

	uint32_t t_SessionId;
	const SDKReturnCode t_SessionIdResult = CoreSdk_GetSessionId(&t_SessionId);
	if (t_SessionIdResult == SDKReturnCode::SDKReturnCode_Success && t_SessionId != 0)
	{
		spdlog::info("Session Id: {}", t_SessionId);
		s_Instance->m_SessionId = t_SessionId;
	}
	else
	{
		spdlog::info("Failed to get the Session ID from Core. The value returned was{}.", t_SessionIdResult);
	}

	ManusHost t_Host(*p_Host);
	s_Instance->m_Host = std::make_unique<ManusHost>(t_Host);

	// Only setting state to displaying data on automatic reconnect
	if (s_Instance->m_State == ClientState::ClientState_Disconnected)
	{
		s_Instance->m_State = ClientState::ClientState_DisplayingData;
	}
}

/// @brief Gets called when the client disconnects from manus core.
/// This callback is optional and in the sample changes the client's state.
void SDKClient::OnDisconnectedCallback(const ManusHost* const p_Host)
{
	spdlog::info("Disconnected from manus core.");
	s_Instance->m_TimeSinceLastDisconnect = std::chrono::high_resolution_clock::now();
	ManusHost t_Host(*p_Host);
	s_Instance->m_Host = std::make_unique<ManusHost>(t_Host);
	s_Instance->m_State = ClientState::ClientState_Disconnected;
}

/// @brief This gets called when the client is connected to manus core
/// @param p_SkeletonStreamInfo contains the meta data on how much data regarding the skeleton we need to get from the SDK.
void SDKClient::OnSkeletonStreamCallback(const SkeletonStreamInfo* const p_SkeletonStreamInfo)
{
	if (s_Instance)
	{
		ClientSkeletonCollection* t_NxtClientSkeleton = new ClientSkeletonCollection();
		t_NxtClientSkeleton->skeletons.resize(p_SkeletonStreamInfo->skeletonsCount);

		for (uint32_t i = 0; i < p_SkeletonStreamInfo->skeletonsCount; i++)
		{
			CoreSdk_GetSkeletonInfo(i, &t_NxtClientSkeleton->skeletons[i].info);
			t_NxtClientSkeleton->skeletons[i].nodes.resize(t_NxtClientSkeleton->skeletons[i].info.nodesCount);
			t_NxtClientSkeleton->skeletons[i].info.publishTime = p_SkeletonStreamInfo->publishTime;
			CoreSdk_GetSkeletonData(i, t_NxtClientSkeleton->skeletons[i].nodes.data(), t_NxtClientSkeleton->skeletons[i].info.nodesCount);
		}
		s_Instance->m_SkeletonMutex.lock();
		if (s_Instance->m_NextSkeleton != nullptr) delete s_Instance->m_NextSkeleton;
		s_Instance->m_NextSkeleton = t_NxtClientSkeleton;
		s_Instance->m_SkeletonMutex.unlock();
	}
}

/// @brief This gets called when the client is connected to manus core. It sends the skeleton data coming from the estimation system, before the retargeting to the client skeleton model. 
/// @param p_RawSkeletonStreamInfo contains the meta data on how much data regarding the raw skeleton we need to get from the SDK.
void SDKClient::OnRawSkeletonStreamCallback(const SkeletonStreamInfo* const p_RawSkeletonStreamInfo)
{
	if (s_Instance)
	{
		ClientRawSkeletonCollection* t_NxtClientRawSkeleton = new ClientRawSkeletonCollection();
		t_NxtClientRawSkeleton->skeletons.resize(p_RawSkeletonStreamInfo->skeletonsCount);

		for (uint32_t i = 0; i < p_RawSkeletonStreamInfo->skeletonsCount; i++)
		{
			CoreSdk_GetRawSkeletonInfo(i, &t_NxtClientRawSkeleton->skeletons[i].info);
			t_NxtClientRawSkeleton->skeletons[i].nodes.resize(t_NxtClientRawSkeleton->skeletons[i].info.nodesCount);
			t_NxtClientRawSkeleton->skeletons[i].info.publishTime = p_RawSkeletonStreamInfo->publishTime;
			CoreSdk_GetRawSkeletonData(i, t_NxtClientRawSkeleton->skeletons[i].nodes.data(), t_NxtClientRawSkeleton->skeletons[i].info.nodesCount);
		}
		s_Instance->m_RawSkeletonMutex.lock();
		if (s_Instance->m_NextRawSkeleton != nullptr) delete s_Instance->m_NextRawSkeleton;
		s_Instance->m_NextRawSkeleton = t_NxtClientRawSkeleton;
		s_Instance->m_RawSkeletonMutex.unlock();
	}
}

/// @brief This gets called when receiving tracker information from core
/// @param p_TrackerStreamInfo contains the meta data on how much data regarding the trackers we need to get from the SDK.
void SDKClient::OnTrackerStreamCallback(const TrackerStreamInfo* const p_TrackerStreamInfo)
{
	if (s_Instance)
	{
		TrackerDataCollection* t_TrackerData = new TrackerDataCollection();

		t_TrackerData->trackerData.resize(p_TrackerStreamInfo->trackerCount);

		for (uint32_t i = 0; i < p_TrackerStreamInfo->trackerCount; i++)
		{
			CoreSdk_GetTrackerData(i, &t_TrackerData->trackerData[i]);
		}
		s_Instance->m_TrackerMutex.lock();
		if (s_Instance->m_NextTrackerData != nullptr) delete s_Instance->m_NextTrackerData;
		s_Instance->m_NextTrackerData = t_TrackerData;
		s_Instance->m_TrackerMutex.unlock();
	}
}

/// @brief This gets called when receiving gesture data from Manus Core
/// In our sample we only save the first glove's gesture data.
/// Gesture data gets generated and sent when glove data changes, this means that the stream
/// does not always contain ALL of the devices, because some may not have had new data since
/// the last time the gesture data was sent.
/// @param p_GestureStream contains the basic info to retrieve gesture data.
void SDKClient::OnGestureStreamCallback(const GestureStreamInfo* const p_GestureStream)
{
	if (s_Instance)
	{
		for (uint32_t i = 0; i < p_GestureStream->gestureProbabilitiesCount; i++)
		{
			GestureProbabilities t_Probs;
			CoreSdk_GetGestureStreamData(i, 0, &t_Probs);
			if (t_Probs.isUserID)continue;
			if (t_Probs.id != s_Instance->m_FirstLeftGloveID && t_Probs.id != s_Instance->m_FirstRightGloveID)continue;
			ClientGestures* t_Gest = new ClientGestures();
			t_Gest->info = t_Probs;
			t_Gest->probabilities.reserve(t_Gest->info.totalGestureCount);
			uint32_t t_BatchCount = (t_Gest->info.totalGestureCount / MAX_GESTURE_DATA_CHUNK_SIZE) + 1;
			uint32_t t_ProbabilityIdx = 0;
			for (uint32_t b = 0; b < t_BatchCount; b++)
			{
				for (uint32_t j = 0; j < t_Probs.gestureCount; j++)
				{
					t_Gest->probabilities.push_back(t_Probs.gestureData[j]);
				}
				t_ProbabilityIdx += t_Probs.gestureCount;
				CoreSdk_GetGestureStreamData(i, t_ProbabilityIdx, &t_Probs); //this will get more data, if needed for the next iteration.
			}

			s_Instance->m_GestureMutex.lock();
			if (t_Probs.id == s_Instance->m_FirstLeftGloveID)
			{
				if (s_Instance->m_NewFirstLeftGloveGestures != nullptr) delete s_Instance->m_NewFirstLeftGloveGestures;
				s_Instance->m_NewFirstLeftGloveGestures = t_Gest;
			}
			else
			{
				if (s_Instance->m_NewFirstRightGloveGestures != nullptr) delete s_Instance->m_NewFirstRightGloveGestures;
				s_Instance->m_NewFirstRightGloveGestures = t_Gest;
			}
			s_Instance->m_GestureMutex.unlock();
		}
	}
}

/// @brief This gets called when receiving landscape information from core
/// @param p_Landscape contains the new landscape from core.
void SDKClient::OnLandscapeCallback(const Landscape* const p_Landscape)
{
	if (s_Instance == nullptr)return;

	Landscape* t_Landscape = new Landscape(*p_Landscape);
	s_Instance->m_LandscapeMutex.lock();
	if (s_Instance->m_NewLandscape != nullptr) delete s_Instance->m_NewLandscape;
	s_Instance->m_NewLandscape = t_Landscape;
	s_Instance->m_NewGestureLandscapeData.resize(t_Landscape->gestureCount);
	CoreSdk_GetGestureLandscapeData(s_Instance->m_NewGestureLandscapeData.data(), (uint32_t)s_Instance->m_NewGestureLandscapeData.size());
	s_Instance->m_LandscapeMutex.unlock();
}


/// @brief This gets called when receiving a system message from Core.
/// @param p_SystemMessage contains the system message received from core.
void SDKClient::OnSystemCallback(const SystemMessage* const p_SystemMessage)
{
	if (s_Instance)
	{
		s_Instance->m_SystemMessageMutex.lock();

		switch (p_SystemMessage->type)
		{
		case SystemMessageType::SystemMessageType_TemporarySkeletonModified:
			// if the message was triggered by a temporary skeleton being modified then save the skeleton index,
			// this information will be used to get and load the skeleton into core
			s_Instance->m_ModifiedSkeletonIndex = p_SystemMessage->infoUInt;
			break;
		default:
			s_Instance->m_SystemMessageCode = p_SystemMessage->type;
			s_Instance->m_SystemMessage = p_SystemMessage->infoString;
			break;
		}
		s_Instance->m_SystemMessageMutex.unlock();
	}
}

/// @brief This gets called when receiving ergonomics data from Manus Core
/// In our sample we only save the first left and first right glove's latests ergonomics data.
/// Ergonomics data gets generated and sent when glove data changes, this means that the stream
/// does not always contain ALL of the devices, because some may not have had new data since
/// the last time the ergonomics data was sent.
/// @param p_Ergo contains the ergonomics data for each glove connected to Core.
void SDKClient::OnErgonomicsCallback(const ErgonomicsStream* const p_Ergo)
{
	if (s_Instance)
	{
		for (uint32_t i = 0; i < p_Ergo->dataCount; i++)
		{
			std::cout << "Hello" << std::endl;
			if (p_Ergo->data[i].isUserID)continue;

			ErgonomicsData* t_Ergo = nullptr;
			if (p_Ergo->data[i].id == s_Instance->m_FirstLeftGloveID)
			{
				t_Ergo = &s_Instance->m_LeftGloveErgoData;
			}
			if (p_Ergo->data[i].id == s_Instance->m_FirstRightGloveID)
			{
				t_Ergo = &s_Instance->m_RightGloveErgoData;
			}
			if (t_Ergo == nullptr)continue;
			CoreSdk_GetTimestampInfo(p_Ergo->publishTime, &s_Instance->m_ErgoTimestampInfo);
			t_Ergo->id = p_Ergo->data[i].id;
			t_Ergo->isUserID = p_Ergo->data[i].isUserID;
			for (int j = 0; j < ErgonomicsDataType::ErgonomicsDataType_MAX_SIZE; j++)
			{
				t_Ergo->data[j] = p_Ergo->data[i].data[j];
			}
		}
	}
}

/// @brief Round the given float value so that it has no more than the given number of decimals.
float SDKClient::RoundFloatValue(float p_Value, int p_NumDecimalsToKeep)
{
	// Since C++11, powf is supposed to be declared in <cmath>.
	// Unfortunately, gcc decided to be non-compliant on this for no apparent
	// reason, so now we have to do this.
	// https://stackoverflow.com/questions/5483930/powf-is-not-a-member-of-std
	float t_Power = static_cast<float>(std::pow(
		10.0,
		static_cast<double>(p_NumDecimalsToKeep)));
	return std::round(p_Value * t_Power) / t_Power;
}

/// @brief Set the position that the next log message will appear at.
/// Using this allows us to have somewhat of a static, yet flexible layout of logging.
void SDKClient::AdvanceConsolePosition(short int p_Y)
{
	if (p_Y < 0)
	{
		m_ConsoleCurrentOffset = 0;
	}
	else
	{
		m_ConsoleCurrentOffset += p_Y;
	}

	ApplyConsolePosition(m_ConsoleCurrentOffset);
}

/// @brief Initialize the sdk, register the callbacks and set the coordinate system.
/// This needs to be done before any of the other SDK functions can be used.
ClientReturnCode SDKClient::InitializeSDK()
{
	// before we can use the SDK, some internal SDK bits need to be initialized.
	// however after initializing, the SDK is not yet connected to a host or doing anything network related just yet.
	const SDKReturnCode t_InitializeResult = CoreSdk_Initialize(m_ClientType);
	if (t_InitializeResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to initialize the Manus Core SDK. The value returned was {}.", t_InitializeResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	const ClientReturnCode t_CallBackResults = RegisterAllCallbacks();
	if (t_CallBackResults != ::ClientReturnCode::ClientReturnCode_Success)
	{
		spdlog::error("Failed to initialize callbacks.");
		return t_CallBackResults;
	}

	// after everything is registered and initialized as seen above
	// we must also set the coordinate system being used for the data in this client.
	// (each client can have their own settings. unreal and unity for instance use different coordinate systems)
	// if this is not set, the SDK will not connect to any Manus core host.
	CoordinateSystemVUH t_VUH;
	CoordinateSystemVUH_Init(&t_VUH);
	t_VUH.handedness = Side::Side_Left; // this is currently set to unreal mode.
	t_VUH.up = AxisPolarity::AxisPolarity_PositiveY;
	t_VUH.view = AxisView::AxisView_ZFromViewer;
	t_VUH.unitScale = 1.0f; //1.0 is meters, 0.01 is cm, 0.001 is mm.

	const SDKReturnCode t_CoordinateResult = CoreSdk_InitializeCoordinateSystemWithVUH(t_VUH, false);
	/* this is an example if you want to use the other coordinate system instead of VUH
	CoordinateSystemDirection t_Direction;
	t_Direction.x = AxisDirection::AD_Right;
	t_Direction.y = AxisDirection::AD_Up;
	t_Direction.z = AxisDirection::AD_Forward;
	const SDKReturnCode t_InitializeResult = CoreSdk_InitializeCoordinateSystemWithDirection(t_Direction);
	*/

	if (t_CoordinateResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to initialize the Manus Core SDK coordinate system. The value returned was {}.", t_InitializeResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief Used to restart and initialize the SDK to make sure a new connection can be set up.
/// This function is used by the client to shutdown the SDK and any connections it has.
/// After that it reinitializes the SDK so that it is ready to connect to a new Manus Core.
ClientReturnCode SDKClient::RestartSDK()
{
	const SDKReturnCode t_ShutDownResult = CoreSdk_ShutDown();
	if (t_ShutDownResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to shutdown the SDK. The value returned was {}.", t_ShutDownResult);
		return ClientReturnCode::ClientReturnCode_FailedToShutDownSDK;
	}

	const ClientReturnCode t_IntializeResult = InitializeSDK();
	if (t_IntializeResult != ClientReturnCode::ClientReturnCode_Success)
	{
		spdlog::error("Failed to initialize the SDK functionality. The value returned was {}.", t_IntializeResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief Used to register the callbacks between sdk and core.
/// Callbacks that are registered functions that get called when a certain 'event' happens, such as data coming in from Manus Core.
/// All of these are optional, but depending on what data you require you may or may not need all of them.
ClientReturnCode SDKClient::RegisterAllCallbacks()
{
	// Register the callback for when manus core is connected to the SDK
	// it is optional, but helps trigger your client nicely if needed.
	// see the function OnConnectedCallback for more details
	const SDKReturnCode t_RegisterConnectCallbackResult = CoreSdk_RegisterCallbackForOnConnect(*OnConnectedCallback);
	if (t_RegisterConnectCallbackResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to register callback function for after connecting to Manus Core. The value returned was {}.", t_RegisterConnectCallbackResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	// Register the callback for when manus core is disconnected to the SDK
	// it is optional, but helps trigger your client nicely if needed.
	// see OnDisconnectedCallback for more details.
	const SDKReturnCode t_RegisterDisconnectCallbackResult = CoreSdk_RegisterCallbackForOnDisconnect(*OnDisconnectedCallback);
	if (t_RegisterDisconnectCallbackResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to register callback function for after disconnecting from Manus Core. The value returned was {}.", t_RegisterDisconnectCallbackResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	// Register the callback for when manus core is sending Skeleton data
	// it is optional, but without it you can not see any resulting skeleton data.
	// see OnSkeletonStreamCallback for more details.
	const SDKReturnCode t_RegisterSkeletonCallbackResult = CoreSdk_RegisterCallbackForSkeletonStream(*OnSkeletonStreamCallback);
	if (t_RegisterSkeletonCallbackResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to register callback function for processing skeletal data from Manus Core. The value returned was {}.", t_RegisterSkeletonCallbackResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	// Register the callback for when manus core is sending landscape data
	// it is optional, but this allows for a reactive adjustment of device information.
	const SDKReturnCode t_RegisterLandscapeCallbackResult = CoreSdk_RegisterCallbackForLandscapeStream(*OnLandscapeCallback);
	if (t_RegisterLandscapeCallbackResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to register callback for landscape from Manus Core. The value returned was {}.", t_RegisterLandscapeCallbackResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	// Register the callback for when manus core is sending System messages
	// This is usually not used by client applications unless they want to show errors/events from core.
	// see OnSystemCallback for more details.
	const SDKReturnCode t_RegisterSystemCallbackResult = CoreSdk_RegisterCallbackForSystemStream(*OnSystemCallback);
	if (t_RegisterSystemCallbackResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to register callback function for system feedback from Manus Core. The value returned was {}.", t_RegisterSystemCallbackResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	// Register the callback for when manus core is sending Ergonomics data
	// it is optional, but helps trigger your client nicely if needed.
	// see OnErgonomicsCallback for more details.
	const SDKReturnCode t_RegisterErgonomicsCallbackResult = CoreSdk_RegisterCallbackForErgonomicsStream(*OnErgonomicsCallback);
	if (t_RegisterErgonomicsCallbackResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to register callback function for ergonomics data from Manus Core. The value returned was {}.", t_RegisterErgonomicsCallbackResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	// Register the callback for when manus core is sending Raw Skeleton data
	// it is optional, but without it you can not see any resulting skeleton data.
	// see OnSkeletonStreamCallback for more details.
	const SDKReturnCode t_RegisterRawSkeletonCallbackResult = CoreSdk_RegisterCallbackForRawSkeletonStream(*OnRawSkeletonStreamCallback);
	if (t_RegisterRawSkeletonCallbackResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to register callback function for processing raw skeletal data from Manus Core. The value returned was {}.", t_RegisterRawSkeletonCallbackResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}

	// Register the callback for when manus core is sending Raw Skeleton data
	// it is optional, but without it you can not see any resulting skeleton data.
	// see OnSkeletonStreamCallback for more details.
	const SDKReturnCode t_RegisterTrackerCallbackResult = CoreSdk_RegisterCallbackForTrackerStream(*OnTrackerStreamCallback);
	if (t_RegisterTrackerCallbackResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to register callback function for processing tracker data from Manus Core. The value returned was {}.", t_RegisterTrackerCallbackResult);
		return ClientReturnCode::ClientReturnCode_FailedToInitialize;
	}
	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief Overridable switch states of how the client flow is done.
/// This is the first option screen in the client to determine how the client is going to connect to manus core
/// it sets the m_state based on user input.
ClientReturnCode SDKClient::PickingConnectionType()
{
	if (m_ConsoleClearTickCount == 0)
	{
		ClearConsole();
		AdvanceConsolePosition(-1);

		bool t_BuiltInDebug = false;
		SDKReturnCode t_Result = CoreSdk_WasDllBuiltInDebugConfiguration(&t_BuiltInDebug);
		if (t_Result == SDKReturnCode::SDKReturnCode_Success)
		{
			if (t_BuiltInDebug)
			{
				spdlog::warn("The DLL was built in debug configuration, please rebuild in release before releasing.");
			}
		}
		else
		{
			spdlog::error("Failed to check if the DLL was built in Debug Configuration. The value returned was {}.", t_Result);
		}

		spdlog::info("Press a key to choose a connection type, or [ESC] to exit.");
		spdlog::info("[L] Local -> Automatically connect to Core running on this computer.");
		spdlog::info("[H] Host  -> Find a host running Core anywhere on the network.");
		spdlog::info("[G] GRPC  -> Try to connect to the preset GRPC address (See settings folder).");
	}

	//if (GetKeyDown('L'))
	//{
	spdlog::info("Picked local.");

	m_ShouldConnectLocally = true;
	m_ShouldConnectGRPC = false;
	m_State = ClientState::ClientState_LookingForHosts;
	//}
	if (GetKeyDown('H'))
	{
		spdlog::info("Picked host.");

		m_ShouldConnectLocally = false;
		m_ShouldConnectGRPC = false;
		m_State = ClientState::ClientState_LookingForHosts;
	}
	if (GetKeyDown('G'))
	{
		spdlog::info("Picked GRPC.");

		m_ShouldConnectGRPC = true;
		m_State = ClientState::ClientState_ConnectingToCore;
	}

	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief Simple example of the SDK looking for manus core hosts on the network
/// and display them on screen.
ClientReturnCode SDKClient::LookingForHosts()
{
	spdlog::info("Looking for hosts...");

	// Underlying function will sleep for m_SecondsToFindHosts to allow servers to reply.
	const SDKReturnCode t_StartResult = CoreSdk_LookForHosts(m_SecondsToFindHosts, m_ShouldConnectLocally);
	if (t_StartResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to look for hosts. The error given was {}.", t_StartResult);

		return ClientReturnCode::ClientReturnCode_FailedToFindHosts;
	}

	m_NumberOfHostsFound = 0;
	const SDKReturnCode t_NumberResult = CoreSdk_GetNumberOfAvailableHostsFound(&m_NumberOfHostsFound);
	if (t_NumberResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get the number of available hosts. The error given was {}.", t_NumberResult);

		return ClientReturnCode::ClientReturnCode_FailedToFindHosts;
	}

	if (m_NumberOfHostsFound == 0)
	{
		spdlog::warn("No hosts found.");
		m_State = ClientState::ClientState_NoHostsFound;

		return ClientReturnCode::ClientReturnCode_FailedToFindHosts;
	}

	m_AvailableHosts.reset(new ManusHost[m_NumberOfHostsFound]);
	const SDKReturnCode t_HostsResult = CoreSdk_GetAvailableHostsFound(m_AvailableHosts.get(), m_NumberOfHostsFound);
	if (t_HostsResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get the available hosts. The error given was {}.", t_HostsResult);

		return ClientReturnCode::ClientReturnCode_FailedToFindHosts;
	}
	if (m_ShouldConnectLocally)
	{
		m_State = ClientState::ClientState_ConnectingToCore;
		return ClientReturnCode::ClientReturnCode_Success;
	}

	m_State = ClientState::ClientState_PickingHost;
	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief When no available hosts are found the user can either retry or exit.
ClientReturnCode SDKClient::NoHostsFound()
{
	if (m_ConsoleClearTickCount == 0)
	{
		AdvanceConsolePosition(-1);
		spdlog::info("No hosts were found. Retry?");
		spdlog::info("[R]   retry");
		spdlog::info("[ESC] exit");
	}

	if (GetKeyDown('R'))
	{
		spdlog::info("Retrying.");

		m_State = ClientState::ClientState_PickingConnectionType;
	}

	// Note: escape is handled by default below.
	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief Print the found hosts and give the user the option to select one.
ClientReturnCode SDKClient::PickingHost()
{
	if (m_ConsoleClearTickCount == 0)
	{
		AdvanceConsolePosition(-1);

		spdlog::info("[R]   retry   [ESC] exit");
		spdlog::info("Pick a host to connect to.");
		spdlog::info("Found the following hosts:");

		// Note: only 10 hosts are shown, to match the number of number keys, for easy selection.
		for (unsigned int t_HostNumber = 0; t_HostNumber < 10 && t_HostNumber < m_NumberOfHostsFound; t_HostNumber++)
		{
			spdlog::info(
				"[{}] hostname \"{}\", IP address \"{}\" Version {}.{}.{}",
				t_HostNumber,
				m_AvailableHosts[t_HostNumber].hostName,
				m_AvailableHosts[t_HostNumber].ipAddress,
				m_AvailableHosts[t_HostNumber].manusCoreVersion.major,
				m_AvailableHosts[t_HostNumber].manusCoreVersion.minor,
				m_AvailableHosts[t_HostNumber].manusCoreVersion.patch);
		}
	}

	for (unsigned int t_HostNumber = 0; t_HostNumber < 10 && t_HostNumber < m_NumberOfHostsFound; t_HostNumber++)
	{
		if (GetKeyDown('0' + t_HostNumber))
		{
			spdlog::info("Selected host {}.", t_HostNumber);

			m_HostToConnectTo = t_HostNumber;
			m_State = ClientState::ClientState_ConnectingToCore;

			break;
		}
	}

	if (GetKeyDown('R'))
	{
		spdlog::info("Retrying.");

		m_State = ClientState::ClientState_PickingConnectionType;
	}

	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief After a connection option was selected, the client will now try to connect to manus core via the SDK.
ClientReturnCode SDKClient::ConnectingToCore()
{
	SDKReturnCode t_ConnectResult = SDKReturnCode::SDKReturnCode_Error;

	if (m_ShouldConnectGRPC)
	{
		t_ConnectResult = CoreSdk_ConnectGRPC();
	}
	else
	{
		if (m_ShouldConnectLocally) { m_HostToConnectTo = 0; }
		t_ConnectResult = CoreSdk_ConnectToHost(m_AvailableHosts[m_HostToConnectTo]);
	}

	if (t_ConnectResult == SDKReturnCode::SDKReturnCode_NotConnected)
	{
		m_State = ClientState::ClientState_NoHostsFound;

		return ClientReturnCode::ClientReturnCode_Success; // Differentiating between error and no connect 
	}
	if (t_ConnectResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to connect to Core. The error given was {}.", t_ConnectResult);

		return ClientReturnCode::ClientReturnCode_FailedToConnect;
	}

	m_State = ClientState::ClientState_DisplayingData;

	// Note: a log message from somewhere in the SDK during the connection process can cause text
	// to permanently turn green after this step. Adding a sleep here of 2+ seconds "fixes" the
	// issue. It seems to be caused by a threading issue somewhere, resulting in a log call being
	// interrupted while it is printing the green [info] text. The log output then gets stuck in
	// green mode.

	return ClientReturnCode::ClientReturnCode_Success;
}


/// @brief Some things happen before every display update, no matter what state.
/// They happen here, such as the updating of the landscape and the generated tracker
/// @return 
ClientReturnCode SDKClient::UpdateBeforeDisplayingData()
{
	AdvanceConsolePosition(-1);

	m_SkeletonMutex.lock();
	if (m_NextSkeleton != nullptr)
	{
		if (m_Skeleton != nullptr)delete m_Skeleton;
		m_Skeleton = m_NextSkeleton;
		m_NextSkeleton = nullptr;
	}
	m_SkeletonMutex.unlock();

	m_RawSkeletonMutex.lock();
	if (m_NextRawSkeleton != nullptr)
	{
		if (m_RawSkeleton != nullptr)delete m_RawSkeleton;
		m_RawSkeleton = m_NextRawSkeleton;
		m_NextRawSkeleton = nullptr;
	}
	m_RawSkeletonMutex.unlock();

	m_TrackerMutex.lock();
	if (m_NextTrackerData != nullptr)
	{
		if (m_TrackerData != nullptr)delete m_TrackerData;
		m_TrackerData = m_NextTrackerData;
		m_NextTrackerData = nullptr;
	}
	m_TrackerMutex.unlock();

	m_LandscapeMutex.lock();
	if (m_NewLandscape != nullptr)
	{
		if (m_Landscape != nullptr)
		{
			delete m_Landscape;
		}
		m_Landscape = m_NewLandscape;
		m_NewLandscape = nullptr;
		m_GestureLandscapeData.swap(m_NewGestureLandscapeData);
	}
	m_LandscapeMutex.unlock();

	m_FirstLeftGloveID = 0;
	m_FirstRightGloveID = 0;
	if (m_Landscape == nullptr)return ClientReturnCode::ClientReturnCode_Success;
	for (size_t i = 0; i < m_Landscape->gloveDevices.gloveCount; i++)
	{
		if (m_FirstLeftGloveID == 0 && m_Landscape->gloveDevices.gloves[i].side == Side::Side_Left)
		{
			m_FirstLeftGloveID = m_Landscape->gloveDevices.gloves[i].id;
			continue;
		}
		if (m_FirstRightGloveID == 0 && m_Landscape->gloveDevices.gloves[i].side == Side::Side_Right)
		{
			m_FirstRightGloveID = m_Landscape->gloveDevices.gloves[i].id;
			continue;
		}
	}

	return ClientReturnCode::ClientReturnCode_Success;
}


/// @brief Once the connections are made we loop this function
/// it calls all the input handlers for different aspects of the SDK
/// and then prints any relevant data of it.
ClientReturnCode SDKClient::DisplayingData()
{
	SPDLOG_INFO("<<Main Menu>> [ESC] quit");
	SPDLOG_INFO("[G] Go To Gloves & Dongle Menu");
	SPDLOG_INFO("[S] Go To Skeleton Menu");
	SPDLOG_INFO("[X] Go To Temporary Skeleton Menu");
	SPDLOG_INFO("[T] Go To Tracker Menu");
	SPDLOG_INFO("[D] Go To Landscape Time Info");
	SPDLOG_INFO("[J] Go To Gestures Menu");

	AdvanceConsolePosition(8);

	GO_TO_DISPLAY('G', DisplayingDataGlove);
	GO_TO_DISPLAY('S', DisplayingDataSkeleton);
	GO_TO_DISPLAY('X', DisplayingDataTemporarySkeleton);
	GO_TO_DISPLAY('T', DisplayingDataTracker);
	GO_TO_DISPLAY('D', DisplayingLandscapeTimeData);
	GO_TO_DISPLAY('J', DisplayingDataGestures);

	PrintSystemMessage();

	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief display the ergonomics data of the gloves, and handles haptic commands.
/// @return 
ClientReturnCode SDKClient::DisplayingDataGlove()
{
	SPDLOG_INFO("[Q] Back  <<Gloves & Dongles>> [ESC] quit");
	SPDLOG_INFO("Haptic keys: left:([1]-[5] = pinky-thumb.) right:([6]-[0] = thumb-pinky.)");

	AdvanceConsolePosition(3);

	GO_TO_MENU_IF_REQUESTED();

	HandleHapticCommands();

	PrintErgonomicsData();
	PrintDongleData();
	PrintSystemMessage();

	return ClientReturnCode::ClientReturnCode_Success;
}

ClientReturnCode SDKClient::DisplayingDataSkeleton()
{
	SPDLOG_INFO("[Q] Back  <<Skeleton>> [ESC] quit");
	SPDLOG_INFO("<Skeleton>[N] Load Skeleton [M] Unload Skeleton");
	SPDLOG_INFO("<Skeleton Haptics> left:([1]-[5] = pinky-thumb) right:([6]-[0] = thumb-pinky)");

	AdvanceConsolePosition(4);

	GO_TO_MENU_IF_REQUESTED();

	HandleSkeletonCommands();
	HandleSkeletonHapticCommands();

	PrintSkeletonData();
	PrintSkeletonInfo();
	PrintSystemMessage();

	return ClientReturnCode::ClientReturnCode_Success;
}

ClientReturnCode SDKClient::DisplayingDataTracker()
{
	SPDLOG_INFO("[Q] Back  <<Gloves & Dongles>> [ESC] quit");
	SPDLOG_INFO("[O] Toggle Test Tracker [G] Toggle per user tracker display");

	AdvanceConsolePosition(3);

	GO_TO_MENU_IF_REQUESTED();

	HandleTrackerCommands();
	PrintRawSkeletonData();

	PrintTrackerData();
	PrintSystemMessage();

	return ClientReturnCode::ClientReturnCode_Success;
}

ClientReturnCode SDKClient::DisplayingDataTemporarySkeleton()
{
	SPDLOG_INFO("[Q] Back  <<Temporary Skeleton>> [ESC] quit");
	SPDLOG_INFO("<Skeleton>[A] Auto allocate chains and load skeleton");
	SPDLOG_INFO("<Skeleton>[B] Build Temporary Skeleton [C] Clear Temporary Skeleton [D] Clear All Temporary Skeletons For The Current Session");
	SPDLOG_INFO("<Skeleton>[E] Save Temporary Skeleton To File, [F] Get Temporary Skeleton From File");

	AdvanceConsolePosition(4);

	GO_TO_MENU_IF_REQUESTED();

	HandleTemporarySkeletonCommands();

	PrintTemporarySkeletonInfo();
	GetTemporarySkeletonIfModified();
	AdvanceConsolePosition(4);
	PrintSystemMessage();

	return ClientReturnCode::ClientReturnCode_Success;
}

ClientReturnCode SDKClient::DisplayingLandscapeTimeData()
{
	SPDLOG_INFO("[Q] Back  <<Landscape Time Data>> [ESC] quit");

	AdvanceConsolePosition(2);

	GO_TO_MENU_IF_REQUESTED();

	PrintLandscapeTimeData();

	AdvanceConsolePosition(3);

	PrintSystemMessage();

	return ClientReturnCode::ClientReturnCode_Success;
}

ClientReturnCode SDKClient::DisplayingDataGestures()
{
	SPDLOG_INFO("[Q] Back  <<Gesture Data>> [ESC] quit");
	SPDLOG_INFO("<Gestures>[H] Show other Hand");

	AdvanceConsolePosition(2);

	GO_TO_MENU_IF_REQUESTED();

	HandleGesturesCommands();

	PrintGestureData();

	AdvanceConsolePosition(3);

	PrintSystemMessage();

	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief When the SDK loses the connection with Core the user can either 
/// close the sdk or try to reconnect to a local or to a remote host.
ClientReturnCode SDKClient::DisconnectedFromCore()
{
	if (m_Host == nullptr) { return ClientReturnCode::ClientReturnCode_FailedToConnect; }

	AdvanceConsolePosition(-1);

	auto t_Duration = std::chrono::duration_cast<std::chrono::seconds>(std::chrono::high_resolution_clock::now() - m_TimeSinceLastDisconnect).count();
	spdlog::info("The SDK lost connection with Manus Core {} seconds ago.", t_Duration);
	spdlog::info("[P] Pick a new host.   [ESC] exit");

	AdvanceConsolePosition(3);

	if (m_ShouldConnectGRPC)
	{
		spdlog::info("Automatically trying to reconnect to GRPC address.");

		ClientReturnCode t_ReconnectResult = ReconnectingToCore();
		if (t_ReconnectResult != ClientReturnCode::ClientReturnCode_FailedToConnect)
		{
			return t_ReconnectResult;
		}
	}
	else if (m_ShouldConnectLocally)
	{
		spdlog::info("Automatically trying to reconnect to local host.");

		ClientReturnCode t_ReconnectResult = ReconnectingToCore();
		if (t_ReconnectResult != ClientReturnCode::ClientReturnCode_FailedToConnect)
		{
			return t_ReconnectResult;
		}
	}
	else
	{
		spdlog::info("[R] Try to reconnect to the last host {} at {}.", m_Host->hostName, m_Host->ipAddress);
		if (GetKeyDown('R'))
		{
			spdlog::info("Reconnecting");

			ClientReturnCode t_ReconnectResult = ReconnectingToCore(m_SecondsToAttemptReconnecting, m_MaxReconnectionAttempts);
			if (t_ReconnectResult != ClientReturnCode::ClientReturnCode_FailedToConnect)
			{
				return t_ReconnectResult;
			}
		}
	}

	AdvanceConsolePosition(10);


	if (GetKeyDown('P'))
	{
		spdlog::info("Picking new host.");

		// Restarting and initializing CoreConnection to make sure a new connection can be set up
		const ClientReturnCode t_RestartResult = RestartSDK();
		if (t_RestartResult != ClientReturnCode::ClientReturnCode_Success)
		{
			spdlog::error("Failed to Restart CoreConnection.");
			return ClientReturnCode::ClientReturnCode_FailedToRestart;
		}

		m_State = ClientState::ClientState_PickingConnectionType;
	}

	return ClientReturnCode::ClientReturnCode_Success;
}

/// @brief It is called when the sdk is disconnected from Core and the user select one of the options to reconnect. 
ClientReturnCode SDKClient::ReconnectingToCore(int32_t p_ReconnectionTime, int32_t p_ReconnectionAttempts)
{
	if (p_ReconnectionTime <= 0) { p_ReconnectionTime = std::numeric_limits<int32_t>::max(); }
	if (p_ReconnectionAttempts <= 0) { p_ReconnectionAttempts = std::numeric_limits<int32_t>::max(); }

	// Restarting and initializing CoreConnection to make sure a new connection can be set up
	const ClientReturnCode t_RestartResult = RestartSDK();
	if (t_RestartResult != ClientReturnCode::ClientReturnCode_Success)
	{
		spdlog::error("Failed to Restart CoreConnection.");
		return ClientReturnCode::ClientReturnCode_FailedToRestart;
	}

	std::chrono::high_resolution_clock::time_point t_Start = std::chrono::high_resolution_clock::now();
	int t_Attempt = 0;
	while ((p_ReconnectionAttempts > 0) && (p_ReconnectionTime > 0))
	{
		spdlog::info("Trying to reconnect to {} at {}. Attempt {}.", m_Host->hostName, m_Host->ipAddress, t_Attempt);
		spdlog::info("Attempts remaining: {}. Seconds before time out: {}.", p_ReconnectionAttempts, p_ReconnectionTime);
		if (m_ShouldConnectGRPC)
		{
			SDKReturnCode t_ConnectionResult = CoreSdk_ConnectGRPC();
			if (t_ConnectionResult == SDKReturnCode::SDKReturnCode_Success)
			{
				spdlog::info("Reconnected to ManusCore.");
				return ClientReturnCode::ClientReturnCode_Success;
			}
		}
		else if (m_ShouldConnectLocally)
		{
			ClientReturnCode t_ConnectionResult = LookingForHosts();
			if (t_ConnectionResult == ClientReturnCode::ClientReturnCode_Success)
			{
				spdlog::info("Reconnected to ManusCore.");
				return ClientReturnCode::ClientReturnCode_Success;
			}
		}
		else
		{
			SDKReturnCode t_ConnectionResult = CoreSdk_ConnectToHost(*m_Host.get());
			if (t_ConnectionResult == SDKReturnCode::SDKReturnCode_Success)
			{
				spdlog::info("Reconnected to ManusCore.");
				return ClientReturnCode::ClientReturnCode_Success;
			}
		}
		std::this_thread::sleep_for(std::chrono::milliseconds(m_SleepBetweenReconnectingAttemptsInMs));
		p_ReconnectionTime -= static_cast<int32_t>(std::chrono::duration_cast<std::chrono::seconds>(std::chrono::high_resolution_clock::now() - t_Start).count());
		--p_ReconnectionAttempts;
		++t_Attempt;
	}

	spdlog::info("Failed to reconnect to ManusCore.");
	m_State = ClientState::ClientState_Disconnected;
	return ClientReturnCode::ClientReturnCode_FailedToConnect;
}


/// @brief Prints the ergonomics data of a hand.
/// @param p_ErgoData 
void SDKClient::PrintHandErgoData(ErgonomicsData& p_ErgoData, bool p_Left)
{
	const std::string t_FingerNames[NUM_FINGERS_ON_HAND] = { "[thumb] ", "[index] ", "[middle]", "[ring]  ", "[pinky] " };
	const std::string t_FingerJointNames[NUM_FINGERS_ON_HAND] = { "mcp", "pip", "dip" };
	const std::string t_ThumbJointNames[NUM_FINGERS_ON_HAND] = { "cmc", "mcp", "ip " };

	int t_DataOffset = 0;
	if (!p_Left)t_DataOffset = 20;

	const std::string* t_JointNames = t_ThumbJointNames;
	for (unsigned int t_FingerNumber = 0; t_FingerNumber < NUM_FINGERS_ON_HAND; t_FingerNumber++)
	{
		spdlog::info("{} {} spread: {:>6}, {} stretch: {:>6}, {} stretch: {:>6}, {} stretch: {:>6} ",
		t_FingerNames[t_FingerNumber], // Name of the finger.
		t_JointNames[0],
		RoundFloatValue(p_ErgoData.data[t_DataOffset], 2),
		t_JointNames[0],
		RoundFloatValue(p_ErgoData.data[t_DataOffset + 1], 2),
		t_JointNames[1],
		RoundFloatValue(p_ErgoData.data[t_DataOffset + 2], 2),
		t_JointNames[2],
		RoundFloatValue(p_ErgoData.data[t_DataOffset + 3], 2));
		t_JointNames = t_FingerJointNames;
		t_DataOffset += 4;
	}
}

/// @brief Print the ergonomics data received from Core.
void SDKClient::PrintErgonomicsData()
{
	// for testing purposes we only look at the first 2 gloves available
	spdlog::info(" -- Ergo Timestamp {:02d}:{:02d}:{:02d}.{:03d} ~ {:02d}/{:02d}/{:d}(D/M/Y)",
		m_ErgoTimestampInfo.hour, m_ErgoTimestampInfo.minute, m_ErgoTimestampInfo.second, m_ErgoTimestampInfo.fraction,
		m_ErgoTimestampInfo.day, m_ErgoTimestampInfo.month, m_ErgoTimestampInfo.year);
	spdlog::info(" -- Left Glove -- 0x{:X} - Angles in degrees", m_FirstLeftGloveID);
	if (m_LeftGloveErgoData.id == m_FirstLeftGloveID)
	{
		PrintHandErgoData(m_LeftGloveErgoData, true);
	}
	else
	{
		spdlog::info(" ...No Data...");
	}
	spdlog::info(" -- Right Glove -- 0x{:X} - Angles in degrees", m_FirstRightGloveID);
	if (m_RightGloveErgoData.id == m_FirstRightGloveID)
	{
		PrintHandErgoData(m_RightGloveErgoData, false);
	}
	else
	{
		spdlog::info(" ...No Data...");
	}

	AdvanceConsolePosition(14);
}

void SDKClient::TCP_Send(const std::string& hand_data)
{
	// Implementation of TCP send here
	// This is where you would connect and send `hand_data` to the server
	std::cout << hand_data << std::endl;
	t_tcp_client.send_data(hand_data);

}



/// @brief Print the ergonomics data received from Core.
void SDKClient::SendErgonomicsData()
{
	// Add static time tracking
	static std::chrono::high_resolution_clock::time_point s_LastSendTime = std::chrono::high_resolution_clock::now();

	// Get current time
	auto currentTime = std::chrono::high_resolution_clock::now();
	auto timeSinceLastSend = std::chrono::duration_cast<std::chrono::milliseconds>(currentTime - s_LastSendTime).count();
	
	// Check if enough time has passed since last send
	if (timeSinceLastSend < TCP_DATA_RATE)
	{
		return;
	}

	// Reset timer
	s_LastSendTime = currentTime;

	// TODO: Add a differentiator to differentiate between left and right glove data
	const std::string t_FingerNames[NUM_FINGERS_ON_HAND] = { "thumb", "index", "middle", "ring", "pinky" };
	int t_DataOffset = 0;
	std::stringstream hand_data_array;
	hand_data_array << "L[";

	// Assuming m_LeftGloveErgoData and m_RightGloveErgoData are defined and populated
	if (m_LeftGloveErgoData.id == m_FirstLeftGloveID)
	{
		for (unsigned int t_FingerNumber = 0; t_FingerNumber < NUM_FINGERS_ON_HAND; t_FingerNumber++)
		{
			std::stringstream ss;
			ss << t_FingerNames[t_FingerNumber] << ": ";
			// Append joint angles for each finger
			for (int j = 0; j < 4; j++) { // Assuming there are 4 joints per finger including the wrist
				ss << RoundFloatValue(m_LeftGloveErgoData.data[t_DataOffset + j], 2) << " ";
				hand_data_array << RoundFloatValue(m_LeftGloveErgoData.data[t_DataOffset + j], 2) << " ";
			}
			t_DataOffset += 4; // Move to the next set of joint angles
			// TCP_Send(ss.str()); // Send the data
		}
		hand_data_array << "]";
		TCP_Send(hand_data_array.str());
	}
	else
	{
		spdlog::info(" ...No Left Glove Data...");
	}

	// Reset data offset for right glove
	t_DataOffset = 20;
	// clear hand data array
	hand_data_array.str("");
	hand_data_array << "R[";
	if (m_RightGloveErgoData.id == m_FirstRightGloveID)
	{
		for (unsigned int t_FingerNumber = 0; t_FingerNumber < NUM_FINGERS_ON_HAND; t_FingerNumber++)
		{
			std::stringstream ss;
			ss << t_FingerNames[t_FingerNumber] << ": ";
			// Append joint angles for each finger
			for (int j = 0; j < 4; j++) { // Assuming there are 4 joints per finger including the wrist
				ss << RoundFloatValue(m_RightGloveErgoData.data[t_DataOffset + j], 2) << " ";
				hand_data_array << RoundFloatValue(m_RightGloveErgoData.data[t_DataOffset + j], 2) << " ";
			}
			t_DataOffset += 4; // Move to the next set of joint angles
			// TCP_Send(ss.str()); // Send the data
		}
		hand_data_array << "]";
		TCP_Send(hand_data_array.str());
	}
	else
	{
		spdlog::info(" ...No Right Glove Data...");
	}
}

std::string ConvertDeviceClassTypeToString(DeviceClassType p_Type)
{
	switch (p_Type)
	{
	case DeviceClassType_Dongle:
		return "Dongle";
	case DeviceClassType_Glove:
		return "Glove";
	case DeviceClassType_Glongle:
		return "Glongle (Glove Dongle)";
	default:
		return "Unknown";
	}
}


std::string ConvertDeviceFamilyTypeToString(DeviceFamilyType p_Type)
{
	switch (p_Type)
	{
	case DeviceFamilyType_Prime1:
		return "Prime 1";
	case DeviceFamilyType_Prime2:
		return "Prime 2";
	case DeviceFamilyType_PrimeX:
		return "Prime X";
	case DeviceFamilyType_Quantum:
		return "Quantum";
	case DeviceFamilyType_Prime3:
		return "Prime 3";
	case DeviceFamilyType_Virtual:
		return "Virtual";
	default:
		return "Unknown";
	}
}

/// @brief Print the ergonomics data received from Core.
void SDKClient::PrintDongleData()
{
	// get a dongle id
	uint32_t t_DongleCount = 0;
	if (CoreSdk_GetNumberOfDongles(&t_DongleCount) != SDKReturnCode::SDKReturnCode_Success) return;
	if (t_DongleCount == 0) return; // we got no gloves to work on anyway!

	uint32_t* t_DongleIds = new uint32_t[t_DongleCount]();
	if (CoreSdk_GetDongleIds(t_DongleIds, t_DongleCount) != SDKReturnCode::SDKReturnCode_Success) return;

	DongleLandscapeData t_DongleData;

	for (uint32_t i = 0; i < t_DongleCount; i++)
	{
		SDKReturnCode t_Result = CoreSdk_GetDataForDongle(t_DongleIds[i], &t_DongleData);
		spdlog::info(" -- Dongle -- 0x{:X}", t_DongleData.id);
		if (t_Result == SDKReturnCode::SDKReturnCode_Success)
		{
			spdlog::info(" Type: {} - {}",
				ConvertDeviceClassTypeToString(t_DongleData.classType),
				ConvertDeviceFamilyTypeToString(t_DongleData.familyType));
			spdlog::info(" License: {}", t_DongleData.licenseType);
		}
		else
		{
			spdlog::info(" ...No Data...");
		}
		AdvanceConsolePosition(4);
	}
}

/// @brief Prints the last received system messages received from Core.
void SDKClient::PrintSystemMessage()
{
	m_SystemMessageMutex.lock();
	spdlog::info("Received System data:{} / code:{}", m_SystemMessage, m_SystemMessageCode);
	m_SystemMessageMutex.unlock();
	AdvanceConsolePosition(2);
}

/// @brief Prints the finalized skeleton data received from Core.
/// Since our console cannot render this data visually in 3d (its not in the scope of this client)
/// we only display a little bit of data of the skeletons we receive.
void SDKClient::PrintSkeletonData()
{
	if (m_Skeleton == nullptr || m_Skeleton->skeletons.size() == 0)
	{
		return;
	}

	spdlog::info("Received Skeleton data. skeletons:{} first skeleton id:{}", m_Skeleton->skeletons.size(), m_Skeleton->skeletons[0].info.id);

	AdvanceConsolePosition(2);
}

void SDKClient::PrintRawSkeletonData()
{
	if (m_RawSkeleton == nullptr || m_RawSkeleton->skeletons.size() == 0)
	{
		return;
	}

	if (m_FirstLeftGloveID == 0 && m_FirstRightGloveID == 0) return; // no gloves connected to core

	uint32_t t_NodeCount = 0;
	uint32_t t_GloveId = 0;
	if (m_FirstLeftGloveID != 0)
	{
		t_GloveId = m_FirstLeftGloveID;
	}
	else
	{
		t_GloveId = m_FirstRightGloveID;
	}
	SDKReturnCode t_Result = CoreSdk_GetRawSkeletonNodeCount(t_GloveId, t_NodeCount);
	if (t_Result != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get Estimation Node Count. The error given was {}.", t_Result);
		return;
	}

	// now get the hierarchy data, this can be used to reconstruct the positions of each node in case the user set up the system with a local coordinate system
	// having a node position defined as local means that this will be related to its parent 
	NodeInfo* t_NodeInfo = new NodeInfo[t_NodeCount];
	t_Result = CoreSdk_GetRawSkeletonNodeInfo(t_GloveId, t_NodeInfo);
	if (t_Result != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get Estimation Hierarchy. The error given was {}.", t_Result);
		return;
	}

	spdlog::info("Received Skeleton glove data from the estimation system. skeletons:{} first skeleton glove id:{}", m_RawSkeleton->skeletons.size(), m_RawSkeleton->skeletons[0].info.gloveId);

	AdvanceConsolePosition(2);
}

/// @brief Prints the tracker data
/// Since our console cannot render this data visually in 3d (its not in the scope of this client)
/// we only display a little bit of data of the trackers we receive.
void SDKClient::PrintTrackerData()
{
	spdlog::info("Tracker test active: {}.", m_TrackerTest); //To show that test tracker is being sent to core
	spdlog::info("Per user tracker display: {}.", m_TrackerDataDisplayPerUser);

	AdvanceConsolePosition(2);

	if (m_TrackerDataDisplayPerUser)
	{
		PrintTrackerDataPerUser();
		AdvanceConsolePosition(10);
	}
	else
	{
		PrintTrackerDataGlobal();
		AdvanceConsolePosition(3);
	}

	// now, as a test, print the tracker data received from the stream
	if (m_TrackerData == nullptr || m_TrackerData->trackerData.size() == 0)
	{
		return;
	}

	spdlog::info("Received Tracker data. number of received trackers:{} first tracker type:{}", m_TrackerData->trackerData.size(), m_TrackerData->trackerData[0].trackerType);

	AdvanceConsolePosition(1);
}

/// @brief Prints the tracker data without taking users into account.
/// This shows how one can get the tracker data that is being streamed without caring about users.
void SDKClient::PrintTrackerDataGlobal()
{
	uint32_t t_NumberOfAvailabletrackers = 0;
	SDKReturnCode t_TrackerResult = CoreSdk_GetNumberOfAvailableTrackers(&t_NumberOfAvailabletrackers);
	if (t_TrackerResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get tracker data. The error given was {}.", t_TrackerResult);
		return;
	}

	spdlog::info("received available trackers :{} ", t_NumberOfAvailabletrackers);

	if (t_NumberOfAvailabletrackers == 0) return; // nothing else to do.
	TrackerId* t_TrackerId = new TrackerId[t_NumberOfAvailabletrackers];
	t_TrackerResult = CoreSdk_GetIdsOfAvailableTrackers(t_TrackerId, t_NumberOfAvailabletrackers);
	if (t_TrackerResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get tracker data. The error given was {}.", t_TrackerResult);
		return;
	}
}

/// @brief Prints the tracker data per user, this shows how to access this data for each user.
void SDKClient::PrintTrackerDataPerUser()
{
	uint32_t t_NumberOfAvailableUsers = 0;
	SDKReturnCode t_UserResult = CoreSdk_GetNumberOfAvailableUsers(&t_NumberOfAvailableUsers);
	if (t_UserResult != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get user count. The error given was {}.", t_UserResult);
		return;
	}
	if (t_NumberOfAvailableUsers == 0) return; // nothing to get yet


	for (uint32_t i = 0; i < t_NumberOfAvailableUsers; i++)
	{
		uint32_t t_NumberOfAvailabletrackers = 0;
		SDKReturnCode t_TrackerResult = CoreSdk_GetNumberOfAvailableTrackersForUserIndex(&t_NumberOfAvailabletrackers, i);
		if (t_TrackerResult != SDKReturnCode::SDKReturnCode_Success)
		{
			spdlog::error("Failed to get tracker data. The error given was {}.", t_TrackerResult);
			return;
		}

		if (t_NumberOfAvailabletrackers == 0) continue;

		spdlog::info("received available trackers for user index[{}] :{} ", i, t_NumberOfAvailabletrackers);

		if (t_NumberOfAvailabletrackers == 0) return; // nothing else to do.
		TrackerId* t_TrackerId = new TrackerId[t_NumberOfAvailabletrackers];
		t_TrackerResult = CoreSdk_GetIdsOfAvailableTrackersForUserIndex(t_TrackerId, i, t_NumberOfAvailabletrackers);
		if (t_TrackerResult != SDKReturnCode::SDKReturnCode_Success)
		{
			spdlog::error("Failed to get tracker data. The error given was {}.", t_TrackerResult);
			return;
		}
	}
}

std::string GetFPSEnumName(TimecodeFPS p_FPS)
{
	switch (p_FPS)
	{
	case TimecodeFPS::TimecodeFPS_23_976:
		return "23.976 FPS (24 dropframe)";
	case TimecodeFPS::TimecodeFPS_24:
		return "24 FPS";
	case TimecodeFPS::TimecodeFPS_25:
		return "25 FPS";
	case TimecodeFPS::TimecodeFPS_29_97:
		return "29.97 FPS (30 dropframe)";
	case TimecodeFPS::TimecodeFPS_30:
		return "30 FPS";
	case TimecodeFPS::TimecodeFPS_50:
		return "50 FPS";
	case TimecodeFPS::TimecodeFPS_59_94:
		return "59.94 FPS (60 dropframe)";
	case TimecodeFPS::TimecodeFPS_60:
		return "60 FPS";
	default:
		return "Undefined FPS";
	}
}

void SDKClient::PrintLandscapeTimeData()
{
	spdlog::info("Total count of Interfaces: {}", m_Landscape->time.interfaceCount);
	spdlog::info("Current Interface: {} {} at index {}", m_Landscape->time.currentInterface.name, m_Landscape->time.currentInterface.api, m_Landscape->time.currentInterface.index);

	spdlog::info("FPS: {}", GetFPSEnumName(m_Landscape->time.fps));
	spdlog::info("Fake signal: {} | Sync Pulse: {} | Sync Status: {}", m_Landscape->time.fakeTimecode, m_Landscape->time.useSyncPulse, m_Landscape->time.syncStatus);
	spdlog::info("Device keep alive: {} | Timecode Status: {}", m_Landscape->time.deviceKeepAlive, m_Landscape->time.timecodeStatus);

	AdvanceConsolePosition(6);
}

void SDKClient::PrintGestureData()
{
	ClientGestures* t_Gest = m_FirstLeftGloveGestures;
	std::string t_Side = "Left";
	if (!m_ShowLeftGestures)
	{
		t_Side = "Right";
		t_Gest = m_FirstRightGloveGestures;
	}

	if (t_Gest == nullptr)
	{
		spdlog::info("No Gesture information for first {} glove.", t_Side);
		AdvanceConsolePosition(3);
		return;
	}
	spdlog::info("Total count of gestures for the {} glove: {}", t_Side, t_Gest->info.totalGestureCount);
	uint32_t t_Max = t_Gest->info.totalGestureCount;
	if (t_Max > 20) t_Max = 20;
	spdlog::info("Showing result of first {} gestures.", t_Max);
	for (uint32_t i = 0; i < t_Max; i++)
	{
		char* t_Name = "";
		for (uint32_t g = 0; g < m_GestureLandscapeData.size(); g++)
		{
			if (m_GestureLandscapeData[g].id == t_Gest->probabilities[i].id)
			{
				t_Name = m_GestureLandscapeData[g].name;
			}
		}
		spdlog::info("Gesture {} ({}) has a probability of {}%.", t_Name, t_Gest->probabilities[i].id, t_Gest->probabilities[i].percent * 100.0f);
	}

	AdvanceConsolePosition(6);
}

/// @brief Prints the type of the first chain generated by the AllocateChain function, this is used for testing.
void SDKClient::PrintSkeletonInfo()
{
	switch (m_ChainType)
	{
	case ChainType::ChainType_FingerIndex:
	{
		spdlog::info("received Skeleton chain type: ChainType_FingerIndex");
		break;
	}
	case ChainType::ChainType_FingerMiddle:
	{
		spdlog::info("received Skeleton chain type: ChainType_FingerMiddle");
		break;
	}
	case ChainType::ChainType_FingerPinky:
	{
		spdlog::info("received Skeleton chain type: ChainType_FingerPinky");
		break;
	}
	case ChainType::ChainType_FingerRing:
	{
		spdlog::info("received Skeleton chain type: ChainType_FingerRing");
		break;
	}
	case ChainType::ChainType_FingerThumb:
	{
		spdlog::info("received Skeleton chain type: ChainType_FingerThumb");
		break;
	}
	case ChainType::ChainType_Hand:
	{
		spdlog::info("received Skeleton chain type: ChainType_Hand");
		break;
	}
	case ChainType::ChainType_Head:
	{
		spdlog::info("received Skeleton chain type: ChainType_Head");
		break;
	}
	case ChainType::ChainType_Leg:
	{
		spdlog::info("received Skeleton chain type: ChainType_Leg");
		break;
	}
	case ChainType::ChainType_Neck:
	{
		spdlog::info("received Skeleton chain type: ChainType_Neck");
		break;
	}
	case ChainType::ChainType_Pelvis:
	{
		spdlog::info("received Skeleton chain type: ChainType_Pelvis");
		break;
	}
	case ChainType::ChainType_Shoulder:
	{
		spdlog::info("received Skeleton chain type: ChainType_Shoulder");
		break;
	}
	case ChainType::ChainType_Spine:
	{
		spdlog::info("received Skeleton chain type: ChainType_Spine");
		break;
	}
	case ChainType::ChainType_Arm:
	{
		spdlog::info("received Skeleton chain type: ChainType_Arm");
		break;
	}
	case ChainType::ChainType_Invalid:
	default:
	{
		spdlog::info("received Skeleton chain type: ChainType_Invalid");
		break;
	}
	}
	AdvanceConsolePosition(2);
}

/// @brief This support function checks if a temporary skeleton related to the current session has been modified and gets it.
/// Whenever the Dev Tools saves the changes to the skeleton, it sets the boolean t_IsSkeletonModified to true for that skeleton.
/// With callback OnSystemCallback this application can be notified when one of its temporary skeletons has been modified, so it can get it and, potentially, load it.
void SDKClient::GetTemporarySkeletonIfModified()
{
	// if a temporary skeleton associated to the current session has been modified we can get it and, potentially, load it 
	if (m_ModifiedSkeletonIndex != UINT_MAX)
	{
		// get the temporary skeleton
		uint32_t t_SessionId = m_SessionId;
		SDKReturnCode t_Res = CoreSdk_GetTemporarySkeleton(m_ModifiedSkeletonIndex, t_SessionId);
		if (t_Res != SDKReturnCode::SDKReturnCode_Success)
		{
			spdlog::error("Failed to get temporary skeleton. The error given was {}.", t_Res);
			return;
		}

		// At this point if we are satisfied with the modifications to the skeleton we can load it into Core.
		// Remember to always call function CoreSdk_ClearTemporarySkeleton after loading a temporary skeleton,
		// this will keep the temporary skeleton list in sync between Core and the SDK.

		//uint32_t t_ID = 0;
		//SDKReturnCode t_Res = CoreSdk_LoadSkeleton(m_ModifiedSkeletonIndex, &t_ID);
		//if (t_Res != SDKReturnCode::SDKReturnCode_Success)
		//{
		//	spdlog::error("Failed to load skeleton. The error given was {}.", t_Res);
		//	return;
		//}
		//if (t_ID == 0)
		//{
		//	spdlog::error("Failed to give skeleton an ID.");
		//}
		//m_LoadedSkeletons.push_back(t_ID);
		//t_Res = CoreSdk_ClearTemporarySkeleton(m_ModifiedSkeletonIndex, m_SessionId);
		//if (t_Res != SDKReturnCode::SDKReturnCode_Success)
		//{
		//	spdlog::error("Failed to clear temporary skeleton. The error given was {}.", t_Res);
		//	return;
		//}
		m_ModifiedSkeletonIndex = UINT_MAX;
	}
}
/// @brief This support function gets the temporary skeletons for all sessions connected to Core and it prints the total number of temporary skeletons associated to the current session.
/// Temporary skeletons are used for auto allocation and in the Dev Tools.
void SDKClient::PrintTemporarySkeletonInfo()
{
	spdlog::info("Number of temporary skeletons in the SDK: {} ", m_TemporarySkeletons.size());

	static uint32_t t_TotalNumberOfTemporarySkeletonsInCore = 0;
	auto t_TimeSinceLastTemporarySkeletonUpdate = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - m_LastTemporarySkeletonUpdate).count();
	if (t_TimeSinceLastTemporarySkeletonUpdate < static_cast<unsigned int>(MILLISECONDS_BETWEEN_TEMPORARY_SKELETONS_UPDATE))
	{
		spdlog::info("Total number of temporary skeletons in core: {} ", t_TotalNumberOfTemporarySkeletonsInCore);
		return;
	}
	TemporarySkeletonCountForAllSessions t_TemporarySkeletonCountForAllSessions;
	SDKReturnCode t_Res = CoreSdk_GetTemporarySkeletonCountForAllSessions(&t_TemporarySkeletonCountForAllSessions);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get all temporary skeletons. The error given was {}.", t_Res);
		return;
	}

	t_TotalNumberOfTemporarySkeletonsInCore = 0;
	for (uint32_t i = 0; i < t_TemporarySkeletonCountForAllSessions.sessionsCount; i++)
	{
		t_TotalNumberOfTemporarySkeletonsInCore += t_TemporarySkeletonCountForAllSessions.temporarySkeletonCountForSessions[i].skeletonCount;
	}

	// print total number of temporary skeletons:
	spdlog::info("Total number of temporary skeletons in core: {} ", t_TotalNumberOfTemporarySkeletonsInCore);
	m_LastTemporarySkeletonUpdate = std::chrono::high_resolution_clock::now();
}

/// @brief This showcases haptics support on gloves.
/// Send haptics commands to connected gloves if specific keys were pressed.
/// We have two ways of sending the vibration commands, based on the dongle id or based on the skeleton id.
void SDKClient::HandleHapticCommands()
{
	if (m_FirstLeftGloveID == 0 && m_FirstRightGloveID == 0) return; // we got no gloves to work on anyway!

	// get a dongle id
	uint32_t t_DongleId = 0;
	uint32_t t_GloveIds[2] = { 0,0 };
	uint32_t t_DongleCount = 0;
	if (CoreSdk_GetNumberOfDongles(&t_DongleCount) != SDKReturnCode::SDKReturnCode_Success) return;
	if (t_DongleCount == 0) return; // we got no gloves to work on anyway!

	uint32_t* t_DongleIds = new uint32_t[t_DongleCount]();
	if (CoreSdk_GetDongleIds(t_DongleIds, t_DongleCount) != SDKReturnCode::SDKReturnCode_Success) return;

	for (uint32_t i = 0; i < t_DongleCount; i++)
	{
		// now lets see if it has gloves. otherwise its still not useful
		CoreSdk_GetGlovesForDongle(t_DongleIds[i], &t_GloveIds[0], &t_GloveIds[1]);
		if (!t_GloveIds[0] && !t_GloveIds[1]) continue;
		t_DongleId = t_DongleIds[i]; // during tests we only expect 1 or 2 gloves, so this code is ok, in more real situation we want to make sure we got the right dongle instead of the first available.
		break;
	}
	if (t_DongleId == 0) return; // still no valid data. (though this is very unlikely)	

	ClientHapticSettings t_HapticState[NUMBER_OF_HANDS_SUPPORTED]{};
	const int t_LeftHand = 0;
	const int t_RightHand = 1;

	// The strange key number sequence here results from having gloves lie in front of you, and have the keys and haptics in the same order.
	t_HapticState[t_LeftHand].shouldHapticFinger[0] = GetKey('5'); // left thumb
	t_HapticState[t_LeftHand].shouldHapticFinger[1] = GetKey('4'); // left index
	t_HapticState[t_LeftHand].shouldHapticFinger[2] = GetKey('3'); // left middle
	t_HapticState[t_LeftHand].shouldHapticFinger[3] = GetKey('2'); // left ring
	t_HapticState[t_LeftHand].shouldHapticFinger[4] = GetKey('1'); // left pinky
	t_HapticState[t_RightHand].shouldHapticFinger[0] = GetKey('6'); // right thumb
	t_HapticState[t_RightHand].shouldHapticFinger[1] = GetKey('7'); // right index
	t_HapticState[t_RightHand].shouldHapticFinger[2] = GetKey('8'); // right middle
	t_HapticState[t_RightHand].shouldHapticFinger[3] = GetKey('9'); // right ring
	t_HapticState[t_RightHand].shouldHapticFinger[4] = GetKey('0'); // right pinky

	// Note: this timer is apparently not very accurate.
	// It is good enough for this test client, but should probably be replaced for other uses.
	static std::chrono::high_resolution_clock::time_point s_TimeOfLastHapticsCommandSent;
	const std::chrono::high_resolution_clock::time_point s_Now = std::chrono::high_resolution_clock::now();
	const long long s_MillisecondsSinceLastHapticCommand = std::chrono::duration_cast<std::chrono::milliseconds>(s_Now - s_TimeOfLastHapticsCommandSent).count();

	if (s_MillisecondsSinceLastHapticCommand < static_cast<unsigned int>(MINIMUM_MILLISECONDS_BETWEEN_HAPTICS_COMMANDS))
	{
		return;
	}

	const Side s_Hands[NUMBER_OF_HANDS_SUPPORTED] = { Side::Side_Left, Side::Side_Right };
	const float s_FullPower = 1.0f;

	for (unsigned int t_HandNumber = 0; t_HandNumber < NUMBER_OF_HANDS_SUPPORTED; t_HandNumber++)
	{
		if (t_GloveIds[t_HandNumber] == 0) continue; // no glove available. skip.

		GloveLandscapeData t_Glove;
		if (CoreSdk_GetDataForGlove_UsingGloveId(t_GloveIds[t_HandNumber], &t_Glove) != SDKReturnCode::SDKReturnCode_Success)
		{
			continue;
		}

		if (t_Glove.familyType != DeviceFamilyType::DeviceFamilyType_Prime1)
		{
			continue;
		}
	}

	// This is an example that shows how to send the haptics commands based on dongle id:
	uint32_t* t_HapticsDongles = new uint32_t[MAX_NUMBER_OF_DONGLES];
	for (unsigned int t_HandNumber = 0; t_HandNumber < NUMBER_OF_HANDS_SUPPORTED; t_HandNumber++)
	{
		uint32_t t_NumberOfHapticsDongles = 0;
		if ((CoreSdk_GetNumberOfHapticsDongles(&t_NumberOfHapticsDongles) != SDKReturnCode::SDKReturnCode_Success) ||
			(t_NumberOfHapticsDongles == 0))
		{
			continue;
		}

		if (CoreSdk_GetHapticsDongleIds(t_HapticsDongles, t_NumberOfHapticsDongles) != SDKReturnCode::SDKReturnCode_Success)
		{
			continue;
		}

		float t_HapticsPowers[NUM_FINGERS_ON_HAND]{};
		for (unsigned int t_FingerNumber = 0; t_FingerNumber < NUM_FINGERS_ON_HAND; t_FingerNumber++)
		{
			t_HapticsPowers[t_FingerNumber] = t_HapticState[t_HandNumber].shouldHapticFinger[t_FingerNumber] ? s_FullPower : 0.0f;
		}

		GloveLandscapeData t_GloveLandscapeData;
		if (CoreSdk_GetDataForGlove_UsingGloveId(t_GloveIds[t_HandNumber], &t_GloveLandscapeData) != SDKReturnCode::SDKReturnCode_Success)
		{
			continue;
		}
		if (!t_GloveLandscapeData.isHaptics) // if the glove is not Haptics do not vibrate.
		{
			continue;
		}

		CoreSdk_VibrateFingers(t_HapticsDongles[0], s_Hands[t_HandNumber], t_HapticsPowers);
	}
	delete[] t_HapticsDongles;
}

/// @brief Handles the console commands for the skeletons.
void SDKClient::HandleSkeletonCommands()
{
	if (GetKeyDown('N'))
	{
		LoadTestSkeleton();
	}
	if (GetKeyDown('M'))
	{
		UnloadTestSkeleton();
	}
}

/// @brief This showcases haptics support on the skeletons.
/// Send haptics commands to the gloves connected to a skeleton if specific keys were pressed.
/// We have two ways of sending the vibration commands, based on the dongle id or based on the skeleton id.
void SDKClient::HandleSkeletonHapticCommands()
{
	if (m_Skeleton == nullptr || m_Skeleton->skeletons.size() == 0)
	{
		return;
	}

	ClientHapticSettings t_HapticState[NUMBER_OF_HANDS_SUPPORTED]{};
	const int t_LeftHand = 0;
	const int t_RightHand = 1;

	// The strange key number sequence here results from having gloves lie in front of you, and have the keys and haptics in the same order.
	t_HapticState[t_LeftHand].shouldHapticFinger[0] = GetKey('5'); // left thumb
	t_HapticState[t_LeftHand].shouldHapticFinger[1] = GetKey('4'); // left index
	t_HapticState[t_LeftHand].shouldHapticFinger[2] = GetKey('3'); // left middle
	t_HapticState[t_LeftHand].shouldHapticFinger[3] = GetKey('2'); // left ring
	t_HapticState[t_LeftHand].shouldHapticFinger[4] = GetKey('1'); // left pinky
	t_HapticState[t_RightHand].shouldHapticFinger[0] = GetKey('6'); // right thumb
	t_HapticState[t_RightHand].shouldHapticFinger[1] = GetKey('7'); // right index
	t_HapticState[t_RightHand].shouldHapticFinger[2] = GetKey('8'); // right middle
	t_HapticState[t_RightHand].shouldHapticFinger[3] = GetKey('9'); // right ring
	t_HapticState[t_RightHand].shouldHapticFinger[4] = GetKey('0'); // right pinky

	// Note: this timer is apparently not very accurate.
	// It is good enough for this test client, but should probably be replaced for other uses.
	static std::chrono::high_resolution_clock::time_point s_TimeOfLastHapticsCommandSent;
	const std::chrono::high_resolution_clock::time_point s_Now = std::chrono::high_resolution_clock::now();
	const long long s_MillisecondsSinceLastHapticCommand = std::chrono::duration_cast<std::chrono::milliseconds>(s_Now - s_TimeOfLastHapticsCommandSent).count();

	if (s_MillisecondsSinceLastHapticCommand < static_cast<unsigned int>(MINIMUM_MILLISECONDS_BETWEEN_HAPTICS_COMMANDS))
	{
		return;
	}

	const Side s_Hands[NUMBER_OF_HANDS_SUPPORTED] = { Side::Side_Left, Side::Side_Right };
	const float s_FullPower = 1.0f;

	// The preferred way of sending the haptics commands is based on skeleton id

	for (unsigned int t_HandNumber = 0; t_HandNumber < NUMBER_OF_HANDS_SUPPORTED; t_HandNumber++)
	{
		float t_HapticsPowers[NUM_FINGERS_ON_HAND]{};
		for (unsigned int t_FingerNumber = 0; t_FingerNumber < NUM_FINGERS_ON_HAND; t_FingerNumber++)
		{
			t_HapticsPowers[t_FingerNumber] = t_HapticState[t_HandNumber].shouldHapticFinger[t_FingerNumber] ? s_FullPower : 0.0f;
		}
		bool t_IsHaptics = false;
		if (CoreSdk_DoesSkeletonGloveSupportHaptics(m_Skeleton->skeletons[0].info.id, s_Hands[t_HandNumber], &t_IsHaptics) != SDKReturnCode::SDKReturnCode_Success)
		{
			continue;
		}
		if (!t_IsHaptics)
		{
			continue;
		}
		CoreSdk_VibrateFingersForSkeleton(m_Skeleton->skeletons[0].info.id, s_Hands[t_HandNumber], t_HapticsPowers);
	}
}

/// @brief Handles the console commands for the temporary skeletons.
void SDKClient::HandleTemporarySkeletonCommands()
{
	if (GetKeyDown('A'))
	{
		AllocateChains();
	}
	if (GetKeyDown('B'))
	{
		BuildTemporarySkeleton();
	}
	if (GetKeyDown('C'))
	{
		ClearTemporarySkeleton();
	}
	if (GetKeyDown('D'))
	{
		ClearAllTemporarySkeletons();
	}
	if (GetKeyDown('E'))
	{
		SaveTemporarySkeletonToFile();
	}
	if (GetKeyDown('F'))
	{
		GetTemporarySkeletonFromFile();
	}
}

/// @brief This support function is used to set a test tracker and add it to the landscape. 
void SDKClient::HandleTrackerCommands()
{
	if (GetKeyDown('O'))
	{
		m_TrackerTest = !m_TrackerTest;
	}

	if (GetKeyDown('G'))
	{
		m_TrackerDataDisplayPerUser = !m_TrackerDataDisplayPerUser;
	}

	if (m_TrackerTest)
	{
		m_TrackerOffset += 0.0005f;
		if (m_TrackerOffset >= 10.0f)
		{
			m_TrackerOffset = 0.0f;
		}

		TrackerId t_TrackerId;
		CopyString(t_TrackerId.id, sizeof(t_TrackerId.id), std::string("Test Tracker"));
		TrackerData t_TrackerData = {};
		t_TrackerData.isHmd = false;
		t_TrackerData.trackerId = t_TrackerId;
		t_TrackerData.trackerType = TrackerType::TrackerType_Unknown;
		t_TrackerData.position = { 0.0f, m_TrackerOffset, 0.0f };
		t_TrackerData.rotation = { 1.0f, 0.0f, 0.0f, 0.0f };
		t_TrackerData.quality = TrackerQuality::TrackingQuality_Trackable;
		TrackerData t_TrackerDatas[MAX_NUMBER_OF_TRACKERS];
		t_TrackerDatas[0] = t_TrackerData;

		const SDKReturnCode t_TrackerSend = CoreSdk_SendDataForTrackers(t_TrackerDatas, 1);
		if (t_TrackerSend != SDKReturnCode::SDKReturnCode_Success)
		{
			spdlog::error("Failed to send tracker data. The error given was {}.", t_TrackerSend);
			return;
		}
	}
}

/// @brief Handles the console commands for the gestures.
void SDKClient::HandleGesturesCommands()
{
	if (GetKeyDown('H'))
	{
		m_ShowLeftGestures = !m_ShowLeftGestures;
	}
}

/// @brief Skeletons are pretty extensive in their data setup
/// so we have several support functions so we can correctly receive and parse the data, 
/// this function helps setup the data.
/// @param p_Id the id of the created node setup
/// @param p_ParentId the id of the node parent
/// @param p_PosX X position of the node, this is defined with respect to the global coordinate system or the local one depending on 
/// the parameter p_UseWorldCoordinates set when initializing the sdk,
/// @param p_PosY Y position of the node this is defined with respect to the global coordinate system or the local one depending on 
/// the parameter p_UseWorldCoordinates set when initializing the sdk,
/// @param p_PosZ Z position of the node this is defined with respect to the global coordinate system or the local one depending on 
/// the parameter p_UseWorldCoordinates set when initializing the sdk,
/// @param p_Name the name of the node setup
/// @return the generated node setup
NodeSetup SDKClient::CreateNodeSetup(uint32_t p_Id, uint32_t p_ParentId, float p_PosX, float p_PosY, float p_PosZ, std::string p_Name)
{
	NodeSetup t_Node;
	NodeSetup_Init(&t_Node);
	t_Node.id = p_Id; //Every ID needs to be unique per node in a skeleton.
	CopyString(t_Node.name, sizeof(t_Node.name), p_Name);
	t_Node.type = NodeType::NodeType_Joint;
	//Every node should have a parent unless it is the Root node.
	t_Node.parentID = p_ParentId; //Setting the node ID to its own ID ensures it has no parent.
	t_Node.settings.usedSettings = NodeSettingsFlag::NodeSettingsFlag_None;

	t_Node.transform.position.x = p_PosX;
	t_Node.transform.position.y = p_PosY;
	t_Node.transform.position.z = p_PosZ;
	return t_Node;
}

ManusVec3 SDKClient::CreateManusVec3(float p_X, float p_Y, float p_Z)
{
	ManusVec3 t_Vec;
	t_Vec.x = p_X;
	t_Vec.y = p_Y;
	t_Vec.z = p_Z;
	return t_Vec;
}

/// @brief This support function sets up the nodes for the skeleton hand
/// In order to have any 3d positional/rotational information from the gloves or body,
/// one needs to setup the skeleton on which this data should be applied.
/// In the case of this sample we create a Hand skeleton for which we want to get the calculated result.
/// The ID's for the nodes set here are the same IDs which are used in the OnSkeletonStreamCallback,
/// this allows us to create the link between Manus Core's data and the data we enter here.
bool SDKClient::SetupHandNodes(uint32_t p_SklIndex)
{
	// Define number of fingers per hand and number of joints per finger
	const uint32_t t_NumFingers = 5;
	const uint32_t t_NumJoints = 4;

	// Create an array with the initial position of each hand node. 
	// Note, these values are just an example of node positions and refer to the hand laying on a flat surface.
	ManusVec3 t_Fingers[t_NumFingers * t_NumJoints] = {
		CreateManusVec3(0.024950f, 0.000000f, 0.025320f), //Thumb CMC joint
		CreateManusVec3(0.000000f, 0.000000f, 0.032742f), //Thumb MCP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.028739f), //Thumb IP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.028739f), //Thumb Tip joint

		//CreateManusVec3(0.011181f, 0.031696f, 0.000000f), //Index CMC joint // Note: we are not adding the matacarpal bones in this example, if you want to animate the metacarpals add each of them to the corresponding finger chain.
		CreateManusVec3(0.011181f, 0.000000f, 0.052904f), //Index MCP joint, if metacarpal is present: CreateManusVec3(0.000000f, 0.000000f, 0.052904f)
		CreateManusVec3(0.000000f, 0.000000f, 0.038257f), //Index PIP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.020884f), //Index DIP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.018759f), //Index Tip joint

		//CreateManusVec3(0.000000f, 0.033452f, 0.000000f), //Middle CMC joint
		CreateManusVec3(0.000000f, 0.000000f, 0.051287f), //Middle MCP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.041861f), //Middle PIP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.024766f), //Middle DIP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.019683f), //Middle Tip joint

		//CreateManusVec3(-0.011274f, 0.031696f, 0.000000f), //Ring CMC joint
		CreateManusVec3(-0.011274f, 0.000000f, 0.049802f),  //Ring MCP joint, if metacarpal is present: CreateManusVec3(0.000000f, 0.000000f, 0.049802f),
		CreateManusVec3(0.000000f, 0.000000f, 0.039736f),  //Ring PIP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.023564f),  //Ring DIP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.019868f),  //Ring Tip joint

		//CreateManusVec3(-0.020145f, 0.027538f, 0.000000f), //Pinky CMC joint
		CreateManusVec3(-0.020145f, 0.000000f, 0.047309f),  //Pinky MCP joint, if metacarpal is present: CreateManusVec3(0.000000f, 0.000000f, 0.047309f),
		CreateManusVec3(0.000000f, 0.000000f, 0.033175f),  //Pinky PIP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.018020f),  //Pinky DIP joint
		CreateManusVec3(0.000000f, 0.000000f, 0.019129f),  //Pinky Tip joint
	};

	// skeleton entry is already done. just the nodes now.
	// setup a very simple node hierarchy for fingers
	// first setup the root node
	// 
	// root, This node has ID 0 and parent ID 0, to indicate it has no parent.
	SDKReturnCode t_Res = CoreSdk_AddNodeToSkeletonSetup(p_SklIndex, CreateNodeSetup(0, 0, 0, 0, 0, "Hand"));
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Add Node To Skeleton Setup. The error given was {}.", t_Res);
		return false;
	}

	// then loop for 5 fingers
	int t_FingerId = 0;
	for (uint32_t i = 0; i < t_NumFingers; i++)
	{
		uint32_t t_ParentID = 0;
		// then the digits of the finger that are linked to the root of the finger.
		for (uint32_t j = 0; j < t_NumJoints; j++)
		{
			t_Res = CoreSdk_AddNodeToSkeletonSetup(p_SklIndex, CreateNodeSetup(1 + t_FingerId + j, t_ParentID, t_Fingers[i * 4 + j].x, t_Fingers[i * 4 + j].y, t_Fingers[i * 4 + j].z, "fingerdigit"));
			if (t_Res != SDKReturnCode::SDKReturnCode_Success)
			{
				printf("Failed to Add Node To Skeleton Setup. The error given %d.", t_Res);
				return false;
			}
			t_ParentID = 1 + t_FingerId + j;
		}
		t_FingerId += t_NumJoints;
	}
	return true;
}

/// @brief This function sets up some basic hand chains.
/// Chains are required for a Skeleton to be able to be animated, it basically tells Manus Core
/// which nodes belong to which body part and what data needs to be applied to which node.
/// @param p_SklIndex The index of the temporary skeleton on which the chains will be added.
/// @return Returns true if everything went fine, otherwise returns false.
bool SDKClient::SetupHandChains(uint32_t p_SklIndex)
{
	// Add the Hand chain, this identifies the wrist of the hand
	{
		ChainSettings t_ChainSettings;
		ChainSettings_Init(&t_ChainSettings);
		t_ChainSettings.usedSettings = ChainType::ChainType_Hand;
		t_ChainSettings.hand.handMotion = HandMotion::HandMotion_IMU;
		t_ChainSettings.hand.fingerChainIdsUsed = 5; //we will have 5 fingers
		t_ChainSettings.hand.fingerChainIds[0] = 1; //links to the other chains we will define further down
		t_ChainSettings.hand.fingerChainIds[1] = 2;
		t_ChainSettings.hand.fingerChainIds[2] = 3;
		t_ChainSettings.hand.fingerChainIds[3] = 4;
		t_ChainSettings.hand.fingerChainIds[4] = 5;

		ChainSetup t_Chain;
		ChainSetup_Init(&t_Chain);
		t_Chain.id = 0; //Every ID needs to be unique per chain in a skeleton.
		t_Chain.type = ChainType::ChainType_Hand;
		t_Chain.dataType = ChainType::ChainType_Hand;
		t_Chain.side = Side::Side_Left;
		t_Chain.dataIndex = 0;
		t_Chain.nodeIdCount = 1;
		t_Chain.nodeIds[0] = 0; //this links to the hand node created in the SetupHandNodes
		t_Chain.settings = t_ChainSettings;

		SDKReturnCode t_Res = CoreSdk_AddChainToSkeletonSetup(p_SklIndex, t_Chain);
		if (t_Res != SDKReturnCode::SDKReturnCode_Success)
		{
			spdlog::error("Failed to Add Chain To Skeleton Setup. The error given was {}.", t_Res);
			return false;
		}
	}

	// Add the 5 finger chains
	const ChainType t_FingerTypes[5] = { ChainType::ChainType_FingerThumb,
		ChainType::ChainType_FingerIndex,
		ChainType::ChainType_FingerMiddle,
		ChainType::ChainType_FingerRing,
		ChainType::ChainType_FingerPinky };
	for (int i = 0; i < 5; i++)
	{
		ChainSettings t_ChainSettings;
		ChainSettings_Init(&t_ChainSettings);
		t_ChainSettings.usedSettings = t_FingerTypes[i];
		t_ChainSettings.finger.handChainId = 0; //This links to the wrist chain above.
		//This identifies the metacarpal bone, if none exists, or the chain is a thumb it should be set to -1.
		//The metacarpal bone should not be part of the finger chain, unless you are defining a thumb which does need it.
		t_ChainSettings.finger.metacarpalBoneId = -1;
		t_ChainSettings.finger.useLeafAtEnd = false; //this is set to true if there is a leaf bone to the tip of the finger.
		ChainSetup t_Chain;
		ChainSetup_Init(&t_Chain);
		t_Chain.id = i + 1; //Every ID needs to be unique per chain in a skeleton.
		t_Chain.type = t_FingerTypes[i];
		t_Chain.dataType = t_FingerTypes[i];
		t_Chain.side = Side::Side_Left;
		t_Chain.dataIndex = 0;
		if (i == 0) // Thumb
		{
			t_Chain.nodeIdCount = 4; //The amount of node id's used in the array
			t_Chain.nodeIds[0] = 1; //this links to the hand node created in the SetupHandNodes
			t_Chain.nodeIds[1] = 2; //this links to the hand node created in the SetupHandNodes
			t_Chain.nodeIds[2] = 3; //this links to the hand node created in the SetupHandNodes
			t_Chain.nodeIds[3] = 4; //this links to the hand node created in the SetupHandNodes
		}
		else // All other fingers
		{
			t_Chain.nodeIdCount = 4; //The amount of node id's used in the array
			t_Chain.nodeIds[0] = (i * 4) + 1; //this links to the hand node created in the SetupHandNodes
			t_Chain.nodeIds[1] = (i * 4) + 2; //this links to the hand node created in the SetupHandNodes
			t_Chain.nodeIds[2] = (i * 4) + 3; //this links to the hand node created in the SetupHandNodes
			t_Chain.nodeIds[3] = (i * 4) + 4; //this links to the hand node created in the SetupHandNodes
		}
		t_Chain.settings = t_ChainSettings;

		SDKReturnCode t_Res = CoreSdk_AddChainToSkeletonSetup(p_SklIndex, t_Chain);
		if (t_Res != SDKReturnCode::SDKReturnCode_Success)
		{
			return false;
		}
	}
	return true;
}

/// @brief This function sets up a very minimalistic hand skeleton.
/// In order to have any 3d positional/rotational information from the gloves or body,
/// one needs to setup a skeleton on which this data can be applied.
/// In the case of this sample we create a Hand skeleton in order to get skeleton information
/// in the OnSkeletonStreamCallback function. This sample does not contain any 3D rendering, so
/// we will not be applying the returned data on anything.
void SDKClient::LoadTestSkeleton()
{
	uint32_t t_SklIndex = 0;

	SkeletonSetupInfo t_SKL;
	SkeletonSetupInfo_Init(&t_SKL);
	t_SKL.type = SkeletonType::SkeletonType_Hand;
	t_SKL.settings.scaleToTarget = true;
	t_SKL.settings.useEndPointApproximations = true;
	t_SKL.settings.targetType = SkeletonTargetType::SkeletonTargetType_UserIndexData;
	//If the user does not exist then the added skeleton will not be animated.
	//Same goes for any other skeleton made for invalid users/gloves.
	t_SKL.settings.skeletonTargetUserIndexData.userIndex = 0;

	CopyString(t_SKL.name, sizeof(t_SKL.name), std::string("LeftHand"));

	SDKReturnCode t_Res = CoreSdk_CreateSkeletonSetup(t_SKL, &t_SklIndex);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Create Skeleton Setup. The error given was {}.", t_Res);
		return;
	}
	m_TemporarySkeletons.push_back(t_SklIndex);

	// setup nodes and chains for the skeleton hand
	if (!SetupHandNodes(t_SklIndex)) return;
	if (!SetupHandChains(t_SklIndex)) return;

	// load skeleton 
	uint32_t t_ID = 0;
	t_Res = CoreSdk_LoadSkeleton(t_SklIndex, &t_ID);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to load skeleton. The error given was {}.", t_Res);
		return;
	}
	RemoveIndexFromTemporarySkeletonList(t_SklIndex);

	if (t_ID == 0)
	{
		spdlog::error("Failed to give skeleton an ID.");
	}
	m_LoadedSkeletons.push_back(t_ID);
}

/// @brief This support function is used to unload a skeleton from Core. 
void SDKClient::UnloadTestSkeleton()
{
	if (m_LoadedSkeletons.size() == 0)
	{
		spdlog::error("There was no skeleton for us to unload.");
		return;
	}
	SDKReturnCode t_Res = CoreSdk_UnloadSkeleton(m_LoadedSkeletons[0]);
	m_LoadedSkeletons.erase(m_LoadedSkeletons.begin());
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to unload skeleton. The error given was {}.", t_Res);

		return;
	}
}



/// @brief This support function sets up an incomplete hand skeleton and then uses manus core to allocate chains for it.
void SDKClient::AllocateChains()
{
	m_ChainType = ChainType::ChainType_Invalid;

	uint32_t t_SklIndex = 0;

	SkeletonSettings t_Settings;
	SkeletonSettings_Init(&t_Settings);
	t_Settings.scaleToTarget = true;
	t_Settings.targetType = SkeletonTargetType::SkeletonTargetType_UserData;
	t_Settings.skeletonTargetUserData.userID = 0;

	SkeletonSetupInfo t_SKL;
	SkeletonSetupInfo_Init(&t_SKL);
	t_SKL.id = 0;
	t_SKL.type = SkeletonType::SkeletonType_Hand;
	t_SKL.settings = t_Settings;
	CopyString(t_SKL.name, sizeof(t_SKL.name), std::string("hand"));

	SDKReturnCode t_Res = CoreSdk_CreateSkeletonSetup(t_SKL, &t_SklIndex);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Create Skeleton Setup. The error given was {}.", t_Res);
		return;
	}
	m_TemporarySkeletons.push_back(t_SklIndex);

	// setup nodes for the skeleton hand
	SetupHandNodes(t_SklIndex);

	// allocate chains for skeleton 
	t_Res = CoreSdk_AllocateChainsForSkeletonSetup(t_SklIndex);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to allocate chains for skeleton. The error given was {}.", t_Res);
		return;
	}

	// get the skeleton info
	SkeletonSetupArraySizes t_SkeletonInfo;
	t_Res = CoreSdk_GetSkeletonSetupArraySizes(t_SklIndex, &t_SkeletonInfo);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get info about skeleton. The error given was {}.", t_Res);
		return;
	}

	ChainSetup* t_Chains = new ChainSetup[t_SkeletonInfo.chainsCount];
	// now get the chain data
	t_Res = CoreSdk_GetSkeletonSetupChains(t_SklIndex, t_Chains);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get skeleton setup chains. The error given was {}.", t_Res);
		delete[] t_Chains;
		return;
	}
	// as proof store the first chain type
	m_ChainType = t_Chains[0].dataType;

	// but since we want to cleanly load the skeleton without holding everything up
	// we need to set its side first
	for (size_t i = 0; i < t_SkeletonInfo.chainsCount; i++)
	{
		if (t_Chains[i].dataType == ChainType::ChainType_Hand)
		{
			t_Chains[i].side = Side::Side_Left; // we're just picking a side here. 

			t_Res = CoreSdk_OverwriteChainToSkeletonSetup(t_SklIndex, t_Chains[i]);
			if (t_Res != SDKReturnCode::SDKReturnCode_Success)
			{
				spdlog::error("Failed to overwrite Chain To Skeleton Setup. The error given was {}.", t_Res);
				delete[] t_Chains;
				return;
			}
			break; // no need to continue checking the others.
		}
	}
	// cleanup
	delete[] t_Chains;

	// load skeleton so it is done. 
	uint32_t t_ID = 0;
	t_Res = CoreSdk_LoadSkeleton(t_SklIndex, &t_ID);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to load skeleton. The error given was {}.", t_Res);
		return;
	}
	RemoveIndexFromTemporarySkeletonList(t_SklIndex);

	if (t_ID == 0)
	{
		spdlog::error("Failed to give skeleton an ID.");
	}
	m_LoadedSkeletons.push_back(t_ID);
}

/// @brief This support function is used for the manual allocation of the skeleton chains with means of a temporary skeleton.
/// Temporary Skeletons can be helpful when the user wants to modify the skeletons chains or nodes more than once before retargeting,
/// as they can be saved in core and retrieved later by the user to apply further modifications. This can be done easily with means of the Dev Tools.
/// The current function contains an example that shows how to create a temporary skeleton, modify its chains, nodes and 
/// skeleton info, and save it into Core. This process should be used during development.
/// After that, the final skeleton should be loaded into core for retargeting and for getting the actual data,as displayed in the LoadTestSkeleton 
/// function.
void SDKClient::BuildTemporarySkeleton()
{
	// define the session Id for which we want to save  
	// in this example we want to save a skeleton for the current session so we use our own Session Id
	uint32_t t_SessionId = m_SessionId;

	bool t_IsSkeletonModified = false; // this bool is set to true by the Dev Tools after saving any modification to the skeleton, 
	// this triggers the OnSyStemCallback which is used in the SDK to be notified about a change to its temporary skeletons.
	// for the purpose of this example setting this bool to true is not really necessary.

	// first create a skeleton setup of type Body
	uint32_t t_SklIndex = 0;

	SkeletonSettings t_Settings;
	SkeletonSettings_Init(&t_Settings);
	t_Settings.scaleToTarget = true;
	t_Settings.targetType = SkeletonTargetType::SkeletonTargetType_UserData;
	t_Settings.skeletonTargetUserData.userID = 0; // this needs to be a real user Id when retargeting, when editing the temporary skeleton this may (hopefully) not cause issues

	SkeletonSetupInfo t_SKL;
	SkeletonSetupInfo_Init(&t_SKL);
	t_SKL.id = 0;
	t_SKL.type = SkeletonType::SkeletonType_Body;
	t_SKL.settings = t_Settings;
	CopyString(t_SKL.name, sizeof(t_SKL.name), std::string("body"));

	SDKReturnCode t_Res = CoreSdk_CreateSkeletonSetup(t_SKL, &t_SklIndex);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Create Skeleton Setup. The error given was {}.", t_Res);
		return;
	}
	m_TemporarySkeletons.push_back(t_SklIndex);
	//Add 3 nodes to the skeleton setup
	t_Res = CoreSdk_AddNodeToSkeletonSetup(t_SklIndex, CreateNodeSetup(0, 0, 0, 0, 0, "root"));
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Add Node To Skeleton Setup. The error given was {}.", t_Res);
		return;
	}

	t_Res = CoreSdk_AddNodeToSkeletonSetup(t_SklIndex, CreateNodeSetup(1, 0, 0, 1, 0, "branch"));
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Add Node To Skeleton Setup. The error given was {}.", t_Res);
		return;
	}

	t_Res = CoreSdk_AddNodeToSkeletonSetup(t_SklIndex, CreateNodeSetup(2, 1, 0, 2, 0, "leaf"));
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Add Node To Skeleton Setup. The error given was {}.", t_Res);
		return;
	}

	//Add one chain of type Leg to the skeleton setup
	ChainSettings t_ChainSettings;
	ChainSettings_Init(&t_ChainSettings);
	t_ChainSettings.usedSettings = ChainType::ChainType_Leg;
	t_ChainSettings.leg.footForwardOffset = 0;
	t_ChainSettings.leg.footSideOffset = 0;
	t_ChainSettings.leg.reverseKneeDirection = false;
	t_ChainSettings.leg.kneeRotationOffset = 0;

	ChainSetup t_Chain;
	ChainSetup_Init(&t_Chain);
	t_Chain.id = 0;
	t_Chain.type = ChainType::ChainType_Leg;
	t_Chain.dataType = ChainType::ChainType_Leg;
	t_Chain.dataIndex = 0;
	t_Chain.nodeIdCount = 3;
	t_Chain.nodeIds[0] = 0;
	t_Chain.nodeIds[1] = 1;
	t_Chain.nodeIds[2] = 2;
	t_Chain.settings = t_ChainSettings;
	t_Chain.side = Side::Side_Left;

	t_Res = CoreSdk_AddChainToSkeletonSetup(t_SklIndex, t_Chain);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Add Chain To Skeleton Setup. The error given was {}.", t_Res);
		return;
	}

	// save the temporary skeleton 
	t_Res = CoreSdk_SaveTemporarySkeleton(t_SklIndex, t_SessionId, t_IsSkeletonModified);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to save temporary skeleton. The error given was {}.", t_Res);
		return;
	}

	// if we want to go on with the modifications to the same temporary skeleton 
	// get the skeleton
	t_Res = CoreSdk_GetTemporarySkeleton(t_SklIndex, t_SessionId);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get temporary skeleton. The error given was {}.", t_Res);
		return;
	}

	// now add second chain to the same temporary skeleton
	t_ChainSettings.usedSettings = ChainType::ChainType_Head;

	t_Chain.id = 1;
	t_Chain.type = ChainType::ChainType_Head;
	t_Chain.dataType = ChainType::ChainType_Head;
	t_Chain.dataIndex = 0;
	t_Chain.nodeIdCount = 1;
	t_Chain.nodeIds[0] = 0;
	t_Chain.settings = t_ChainSettings;
	t_Chain.side = Side::Side_Center;

	t_Res = CoreSdk_AddChainToSkeletonSetup(t_SklIndex, t_Chain);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Add Chain To Skeleton Setup. The error given was {}.", t_Res);
		return;
	}

	// save the temporary skeleton 
	t_Res = CoreSdk_SaveTemporarySkeleton(t_SklIndex, t_SessionId, t_IsSkeletonModified);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to save temporary skeleton. The error given was {}.", t_Res);
		return;
	}

	// get the skeleton info (number of nodes and chains for that skeleton)
	SkeletonSetupArraySizes t_SkeletonInfo;
	t_Res = CoreSdk_GetSkeletonSetupArraySizes(t_SklIndex, &t_SkeletonInfo);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get info about skeleton. The error given was {}.", t_Res);
		return;
	}

	// now get the chain data
	ChainSetup* t_Chains = new ChainSetup[t_SkeletonInfo.chainsCount];
	t_Res = CoreSdk_GetSkeletonSetupChains(t_SklIndex, t_Chains);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get skeleton setup chains. The error given was {}.", t_Res);
		return;
	}

	// get the node data 
	NodeSetup* t_Nodes = new NodeSetup[t_SkeletonInfo.nodesCount];
	t_Res = CoreSdk_GetSkeletonSetupNodes(t_SklIndex, t_Nodes);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get skeleton setup nodes. The error given was {}.", t_Res);
		return;
	}

	// just as an example try to get the skeleton setup info
	SkeletonSetupInfo t_SKeletonSetupInfo;
	SkeletonSetupInfo_Init(&t_SKeletonSetupInfo);
	t_Res = CoreSdk_GetSkeletonSetupInfo(t_SklIndex, &t_SKeletonSetupInfo);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to overwrite Skeleton Setup. The error given was {}.", t_Res);
		return;
	}

	// if we want to modify the skeleton setup or if we want to apply some changes to the chains or nodes:
	// first overwrite the existing skeleton setup and then re-add all the chains and nodes to it
	SkeletonSettings_Init(&t_Settings);
	t_Settings.targetType = SkeletonTargetType::SkeletonTargetType_GloveData;

	t_SKL.settings = t_Settings;
	CopyString(t_SKL.name, sizeof(t_SKL.name), std::string("body2"));

	// this way we overwrite the temporary skeleton with index t_SklIndex with the modified skeleton setup
	t_Res = CoreSdk_OverwriteSkeletonSetup(t_SklIndex, t_SKL);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to overwrite Skeleton Setup. The error given was {}.", t_Res);
		return;
	}

	// modify chains and nodes
	t_Chains[0].side = Side::Side_Right;
	t_Nodes[0].type = NodeType::NodeType_Mesh;

	// add all the existing nodes to the new skeleton setup
	for (size_t i = 0; i < t_SkeletonInfo.nodesCount; i++)
	{
		t_Res = CoreSdk_AddNodeToSkeletonSetup(t_SklIndex, t_Nodes[i]);
		if (t_Res != SDKReturnCode::SDKReturnCode_Success)
		{
			spdlog::error("Failed to Add Node To Skeleton Setup. The error given was {}.", t_Res);
			return;
		}
	}

	// then add all the existing chains to the new skeleton setup
	for (size_t i = 0; i < t_SkeletonInfo.chainsCount; i++)
	{
		t_Res = CoreSdk_AddChainToSkeletonSetup(t_SklIndex, t_Chains[i]);
		if (t_Res != SDKReturnCode::SDKReturnCode_Success)
		{
			spdlog::error("Failed to Add Chains To Skeleton Setup. The error given was {}.", t_Res);
			return;
		}
	}

	// cleanup
	delete[] t_Chains;
	delete[] t_Nodes;

	// save temporary skeleton 
	// in the Dev Tools this bool is set to true when saving the temporary skeleton, this triggers OnSystemCallback which 
	// notifies the SDK sessions about a modifications to one of their temporary skeletons.
	// setting the bool to true in this example is not really necessary, it's just for testing purposes.
	t_IsSkeletonModified = true;
	t_Res = CoreSdk_SaveTemporarySkeleton(t_SklIndex, t_SessionId, t_IsSkeletonModified);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to save temporary skeleton. The error given was {}.", t_Res);
		return;
	}
}

/// @brief This support function is used to clear a temporary skeleton from the temporary skeleton list, for example it can be used when the 
/// max number of temporary skeletons has been reached for a specific session.
void SDKClient::ClearTemporarySkeleton()
{
	// clear the first element of the temporary skeleton list
	if (m_TemporarySkeletons.size() == 0)
	{
		spdlog::error("There are no Temporary Skeletons to clear!");
		return;
	}
	uint32_t t_SklIndex = m_TemporarySkeletons[0];
	SDKReturnCode t_Res = CoreSdk_ClearTemporarySkeleton(t_SklIndex, m_SessionId);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Clear Temporary Skeleton. The error given was {}.", t_Res);
		return;
	}
	m_TemporarySkeletons.erase(m_TemporarySkeletons.begin());
}

/// @brief This support function is used to clear all temporary skeletons associated to the current SDK session, it can be used when the 
/// max number of temporary skeletons has been reached for the current session and we want to make room for more.
void SDKClient::ClearAllTemporarySkeletons()
{
	if (m_TemporarySkeletons.size() == 0)
	{
		spdlog::error("There are no Temporary Skeletons to clear!");
		return;
	}
	SDKReturnCode t_Res = CoreSdk_ClearAllTemporarySkeletons();
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Clear All Temporary Skeletons. The error given was {}.", t_Res);
		return;
	}
	m_TemporarySkeletons.clear();
}

void SDKClient::SaveTemporarySkeletonToFile()
{
	// this example shows how to save a temporary skeleton to a file
	// first create a temporary skeleton:

	// define the session Id for which we want to save  
	uint32_t t_SessionId = m_SessionId;

	bool t_IsSkeletonModified = false; // setting this bool to true is not necessary here, it is mostly used by the Dev Tools
	// to notify the SDK sessions about their skeleton being modified.

	// first create a skeleton setup
	uint32_t t_SklIndex = 0;

	SkeletonSetupInfo t_SKL;
	SkeletonSetupInfo_Init(&t_SKL);
	t_SKL.type = SkeletonType::SkeletonType_Hand;
	t_SKL.settings.scaleToTarget = true;
	t_SKL.settings.targetType = SkeletonTargetType::SkeletonTargetType_GloveData;
	t_SKL.settings.skeletonTargetUserIndexData.userIndex = 0;

	CopyString(t_SKL.name, sizeof(t_SKL.name), std::string("LeftHand"));

	SDKReturnCode t_Res = CoreSdk_CreateSkeletonSetup(t_SKL, &t_SklIndex);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Create Skeleton Setup. The error given was {}.", t_Res);
		return;
	}
	m_TemporarySkeletons.push_back(t_SklIndex);

	// setup nodes and chains for the skeleton hand
	if (!SetupHandNodes(t_SklIndex)) return;
	if (!SetupHandChains(t_SklIndex)) return;

	// save the temporary skeleton 
	t_Res = CoreSdk_SaveTemporarySkeleton(t_SklIndex, t_SessionId, t_IsSkeletonModified);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to save temporary skeleton. The error given was {}.", t_Res);
		return;
	}

	// now compress the temporary skeleton data and get the size of the compressed data:
	uint32_t t_TemporarySkeletonLengthInBytes;

	t_Res = CoreSdk_CompressTemporarySkeletonAndGetSize(t_SklIndex, t_SessionId, &t_TemporarySkeletonLengthInBytes);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to compress temporary skeleton and get size. The error given was {}.", t_Res);
		return;
	}
	unsigned char* t_TemporarySkeletonData = new unsigned char[t_TemporarySkeletonLengthInBytes];

	// get the array of bytes with the compressed temporary skeleton data, remember to always call function CoreSdk_CompressTemporarySkeletonAndGetSize
	// before trying to get the compressed temporary skeleton data
	t_Res = CoreSdk_GetCompressedTemporarySkeletonData(t_TemporarySkeletonData, t_TemporarySkeletonLengthInBytes);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to get compressed temporary skeleton data. The error given was {}.", t_Res);
		return;
	}

	// now save the data into a .mskl file
	// as an example we save the temporary skeleton in a folder called ManusTemporarySkeleton inside the documents directory
	// get the path for the documents directory
	std::string t_DirectoryPathString = GetDocumentsDirectoryPath_UTF8();

	// create directory name and file name for storing the temporary skeleton
	std::string t_DirectoryPath =
		t_DirectoryPathString
		+ s_SlashForFilesystemPath
		+ "ManusTemporarySkeleton";

	CreateFolderIfItDoesNotExist(t_DirectoryPath);

	std::string t_DirectoryPathAndFileName =
		t_DirectoryPath
		+ s_SlashForFilesystemPath
		+ "TemporarySkeleton.mskl";

	// write the temporary skeleton data to .mskl file
	std::ofstream t_File = GetOutputFileStream(t_DirectoryPathAndFileName);
	t_File.write((char*)t_TemporarySkeletonData, t_TemporarySkeletonLengthInBytes);
	t_File.close();

	t_Res = CoreSdk_ClearTemporarySkeleton(t_SklIndex, t_SessionId);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Clear Temporary Skeleton after saving. The error given was {}.", t_Res);
		return;
	}
	RemoveIndexFromTemporarySkeletonList(t_SklIndex);
}


void SDKClient::GetTemporarySkeletonFromFile()
{
	// this example shows how to load a temporary skeleton data from a file

	// as an example we try to get the temporary skeleton data previously saved as .mskl file in directory Documents/ManusTemporarySkeleton
	// get the path for the documents directory
	std::string t_DirectoryPathString = GetDocumentsDirectoryPath_UTF8();

	// check if directory exists
	std::string t_DirectoryPath =
		t_DirectoryPathString
		+ s_SlashForFilesystemPath
		+ "ManusTemporarySkeleton";

	if (!DoesFolderOrFileExist(t_DirectoryPath))
	{
		SPDLOG_WARN("Failed to read from client file, the mentioned directory does not exist");
		return;
	}

	// create string with file name
	std::string t_DirectoryPathAndFileName =
		t_DirectoryPath
		+ s_SlashForFilesystemPath
		+ "TemporarySkeleton.mskl";

	// read from file
	std::ifstream t_File = GetInputFileStream(t_DirectoryPathAndFileName);

	if (!t_File)
	{
		SPDLOG_WARN("Failed to read from client file, the file does not exist in the mentioned directory");
		return;
	}

	// get file dimension
	t_File.seekg(0, t_File.end);
	int t_FileLength = (int)t_File.tellg();
	t_File.seekg(0, t_File.beg);

	// get temporary skeleton data from file
	unsigned char* t_TemporarySkeletonData = new unsigned char[t_FileLength];
	t_File.read((char*)t_TemporarySkeletonData, t_FileLength);
	t_File.close();


	// save the zipped temporary skeleton information, they will be used internally for sending the data to Core
	uint32_t t_TemporarySkeletonLengthInBytes = t_FileLength;

	if (t_TemporarySkeletonData == nullptr)
	{
		SPDLOG_WARN("Failed to read the compressed temporary skeleton data from file");
		delete[] t_TemporarySkeletonData;
		return;
	}

	// create a skeleton setup where we will store the temporary skeleton retrieved from file
	SkeletonSetupInfo t_SKL;
	SkeletonSetupInfo_Init(&t_SKL);
	uint32_t t_SklIndex = 0;
	SDKReturnCode t_Res = CoreSdk_CreateSkeletonSetup(t_SKL, &t_SklIndex);
	if (t_Res != SDKReturnCode::SDKReturnCode_Success)
	{
		spdlog::error("Failed to Create Skeleton Setup. The error given was {}.", t_Res);
		return;
	}
	m_TemporarySkeletons.push_back(t_SklIndex);

	// associate the retrieved temporary skeleton to the current session id
	uint32_t t_SessionId = m_SessionId;

	// load the temporary skeleton data retrieved from the zipped file and save it with index t_SklIndex and session id of the current session
	SDKReturnCode t_Result = CoreSdk_GetTemporarySkeletonFromCompressedData(t_SklIndex, t_SessionId, t_TemporarySkeletonData, t_TemporarySkeletonLengthInBytes);
	if (t_Result != SDKReturnCode::SDKReturnCode_Success)
	{
		SPDLOG_WARN("Failed to load temporary skeleton data from client file in Core, the error code was: {}.", t_Result);
		return;
	}

	delete[] t_TemporarySkeletonData;
}

void SDKClient::TestTimestamp()
{
	ManusTimestamp t_TS;
	ManusTimestamp_Init(&t_TS);
	ManusTimestampInfo t_TSInfo;
	ManusTimestampInfo_Init(&t_TSInfo);
	t_TSInfo.fraction = 69;
	t_TSInfo.second = 6;
	t_TSInfo.minute = 9;
	t_TSInfo.hour = 6;
	t_TSInfo.day = 9;
	t_TSInfo.month = 6;
	t_TSInfo.year = 6969;
	t_TSInfo.timecode = true;

	CoreSdk_SetTimestampInfo(&t_TS, t_TSInfo);

	ManusTimestampInfo t_TSInfo2;
	CoreSdk_GetTimestampInfo(t_TS, &t_TSInfo2);
}

void SDKClient::RemoveIndexFromTemporarySkeletonList(uint32_t p_Idx)
{
	for (int i = 0; i < m_TemporarySkeletons.size(); i++)
	{
		if (m_TemporarySkeletons[i] == p_Idx)
		{
			m_TemporarySkeletons.erase(m_TemporarySkeletons.begin() + i);
		}
	}
}
