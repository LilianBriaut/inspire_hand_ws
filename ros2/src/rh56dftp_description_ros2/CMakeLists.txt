cmake_minimum_required(VERSION 3.16)
project(rh56dftp_description)

find_package(ament_cmake REQUIRED)

# The wrapped framework-agnostic package lives next to this colcon workspace:
#   inspire_hand_ws/rh56dftp_description   <- content (do not modify)
#   inspire_hand_ws/ros2/src/rh56dftp_description_ros2  <- this wrapper
set(WRAPPED_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../../../rh56dftp_description")

if(NOT EXISTS "${WRAPPED_DIR}/urdf/rh56dftp.xacro")
  message(FATAL_ERROR
    "Wrapped package not found at ${WRAPPED_DIR}. This wrapper expects the "
    "framework-agnostic rh56dftp_description directory to sit at the root of "
    "inspire_hand_ws (sibling of the ros2/ colcon workspace).")
endif()

install(
  DIRECTORY
    "${WRAPPED_DIR}/urdf"
    "${WRAPPED_DIR}/meshes"
    "${WRAPPED_DIR}/config"
    "${WRAPPED_DIR}/tactile"
  DESTINATION share/${PROJECT_NAME}
)

install(
  FILES
    "${WRAPPED_DIR}/LICENSE"
    "${WRAPPED_DIR}/NOTICE"
    "${WRAPPED_DIR}/README.md"
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
