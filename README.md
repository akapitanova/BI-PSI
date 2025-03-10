# Robot Navigation Server

## Overview
This project implements a **robot navigation server** that handles client connections,
authentication, and movement commands while managing obstacles and recharging states.

The server follows a strict communication protocol, ensuring proper authentication, 
syntax validation, and movement handling for connected robots.

## Features
- **Multi-threaded server** to handle multiple robot connections.
- **Authentication system** using predefined keys.
- **Movement control** with obstacle avoidance.
- **State management** for different stages of robot interaction.
- **Recharging detection** with timeout handling.
- **Error handling** for syntax, logic, and authentication issues.

## Requirements
- Python 3.x
- Socket module (built-in)
- _thread module (built-in)
- sys and os modules (built-in)

## Installation
   ```sh
   git clone https://github.com/your-repo/robot-navigation-server.git
   cd robot-navigation-server
   python3 server.py <PORT> <HOST>
