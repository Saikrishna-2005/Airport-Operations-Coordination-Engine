from app.tools.weather_data_tool import get_weather_data


def main():
    print("\nTesting Hyderabad Airport Weather")
    print("-" * 40)

    result = get_weather_data("HYD")

    for key, value in result.items():
        print(f"{key}: {value}")

    print("\nTesting Invalid Airport Code")
    print("-" * 40)

    invalid_result = get_weather_data("INVALID")

    for key, value in invalid_result.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()